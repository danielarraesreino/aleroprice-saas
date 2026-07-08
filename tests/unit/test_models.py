from app.models.modelo_produto import Produto
from app.models.modelo_prato import Prato, PratoInsumo
from app.models.modelo_cardapio import CardapioItem

def test_produto_creation(session, restaurant):
    """Testa criação básica de produto"""
    p = Produto(
        nome="Teste Produto",
        unidade="kg",
        preco_unitario=10.00,
        restaurant_id=restaurant.id
    )
    session.add(p)
    session.commit()
    
    assert p.id is not None
    assert p.estoque_atual == 0
    assert p.ativo is True

def test_prato_custo_calculo(session, restaurant):
    """Testa cálculo automático de custo do prato baseado nos insumos"""
    # Criar ingredientes
    ing1 = Produto(nome="Ing1", unidade="kg", preco_unitario=10.00, restaurant_id=restaurant.id)
    ing2 = Produto(nome="Ing2", unidade="kg", preco_unitario=20.00, restaurant_id=restaurant.id)
    session.add_all([ing1, ing2])
    session.commit()
    
    # Criar prato
    prato = Prato(
        nome="Prato Teste",
        rendimento=1,
        unidade_rendimento="porção",
        porcoes_rendimento=1,
        restaurant_id=restaurant.id
    )
    session.add(prato)
    session.commit()
    
    # Adicionar insumos
    # 0.5kg de Ing1 (Custo 5.00) + 0.2kg de Ing2 (Custo 4.00) = Total 9.00
    pi1 = PratoInsumo(prato_id=prato.id, produto_id=ing1.id, quantidade=0.5)
    pi2 = PratoInsumo(prato_id=prato.id, produto_id=ing2.id, quantidade=0.2)
    session.add_all([pi1, pi2])
    session.commit()
    
    # Verificar cálculos
    assert prato.custo_direto_total == 9.00
    assert prato.custo_direto_por_porcao == 9.00 # 1 porção
    
    # Alterar porções
    prato.porcoes_rendimento = 2
    session.commit()
    assert prato.custo_direto_por_porcao == 4.50

def test_cardapio_item_constraints(session, restaurant):
    """Testa restrições e relacionamentos do Item de Cardápio"""
    from app.models.modelo_cardapio import Cardapio, CardapioSecao
    
    # Setup
    c = Cardapio(nome="Cardápio Teste", restaurant_id=restaurant.id)
    session.add(c)
    session.commit()
    
    s = CardapioSecao(nome="Seção Teste", cardapio_id=c.id)
    session.add(s)
    session.commit()
    
    p = Prato(nome="Prato Cardapio", unidade_rendimento="cj", porcoes_rendimento=1, rendimento=1, restaurant_id=restaurant.id)
    session.add(p)
    session.commit()
    
    # Item
    item = CardapioItem(secao_id=s.id, prato_id=p.id, preco_venda=50.00)
    session.add(item)
    session.commit()
    
    assert item.get_preco_venda == 50.00
    assert item.prato.nome == "Prato Cardapio"
