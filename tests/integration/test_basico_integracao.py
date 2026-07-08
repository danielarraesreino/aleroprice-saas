import pytest
from datetime import datetime, timedelta
from sqlalchemy import text
from app.models.modelo_desperdicio import CategoriaDesperdicio, RegistroDesperdicio
from app.models.modelo_produto import Produto

@pytest.fixture
def setup_dados_base(session, restaurant):
    """Cria dados bu00e1sicos para testes de integrau00e7u00e3o"""
    # Criar categorias de desperdu00edcio
    categorias = [
        CategoriaDesperdicio(nome="Vencido", descricao="Alimentos vencidos", cor="#FF0000", restaurant_id=restaurant.id),
        CategoriaDesperdicio(nome="Sobra", descricao="Sobras de produu00e7u00e3o", cor="#FFA500", restaurant_id=restaurant.id),
    ]

    for categoria in categorias:
        session.add(categoria)

    # Criar produtos
    produtos = [
        Produto(
            nome="Arroz",
            descricao="Arroz branco tipo 1",
            unidade="kg",
            preco_unitario=5.0,
            estoque_minimo=10.0,
            estoque_atual=50.0,
            categoria="Alimentos",
            restaurant_id=restaurant.id
        ),
        Produto(
            nome="Feiju00e3o",
            descricao="Feiju00e3o carioca",
            unidade="kg",
            preco_unitario=8.0,
            estoque_minimo=8.0,
            estoque_atual=30.0,
            categoria="Alimentos",
            restaurant_id=restaurant.id
        ),
    ]
    
    for produto in produtos:
        session.add(produto)
    
    session.commit()
    
    return {
        "categorias": categorias,
        "produtos": produtos
    }

def test_fluxo_registro_desperdicio(session, restaurant, setup_dados_base):
    """Testa o fluxo completo de registro e consulta de desperdu00edcio"""
    dados = setup_dados_base
    
    # 1. Obter referências para os dados básicos
    categoria_vencido = dados["categorias"][0]  # Categoria "Vencido"
    produto_arroz = dados["produtos"][0]        # Produto "Arroz"
    
    # 2. Registrar um desperdício
    desperdicio = RegistroDesperdicio(
        categoria_id=categoria_vencido.id,
        produto_id=produto_arroz.id,
        restaurant_id=restaurant.id,
        quantidade=5.0,
        unidade="kg",
        valor_estimado=25.0,  # 5kg a R$5,00/kg
        data_registro=datetime.now(),
        motivo="Produto vencido",
        responsavel="Operador de Teste",
        local="Estoque",
        descricao="Produto encontrado vencido durante inventário"
    )
    session.add(desperdicio)
    session.commit()
    
    # 3. Verificar se o registro foi salvo corretamente
    assert desperdicio.id is not None
    
    # 4. Consultar o registro
    registro_db = session.query(RegistroDesperdicio).filter_by(id=desperdicio.id).first()
    assert registro_db is not None
    assert registro_db.categoria_id == categoria_vencido.id
    assert registro_db.produto_id == produto_arroz.id
    assert registro_db.quantidade == 5.0
    assert registro_db.valor_estimado == 25.0
    
    # 5. Verificar se os relacionamentos estão corretos
    assert registro_db.categoria.nome == "Vencido"
    assert registro_db.produto.nome == "Arroz"
    
    # 6. Verificar se podemos obter todos os registros para uma categoria
    registros_categoria = session.query(RegistroDesperdicio).filter_by(categoria_id=categoria_vencido.id).all()
    assert len(registros_categoria) == 1
    assert registros_categoria[0].id == desperdicio.id
    
    # 7. Verificar se podemos obter todos os registros para um produto
    registros_produto = session.query(RegistroDesperdicio).filter_by(produto_id=produto_arroz.id).all()
    assert len(registros_produto) == 1
    assert registros_produto[0].id == desperdicio.id
    
    # 8. Testar consultas mais complexas (ex: desperdicios por período)
    data_atual = datetime.now()
    data_inicio = data_atual - timedelta(days=1)  # Ontem
    data_fim = data_atual + timedelta(days=1)     # Amanhã
    
    registros_periodo = session.query(RegistroDesperdicio).filter(
        RegistroDesperdicio.data_registro >= data_inicio,
        RegistroDesperdicio.data_registro <= data_fim
    ).all()
    
    assert len(registros_periodo) == 1
    assert registros_periodo[0].id == desperdicio.id
    
    # 9. Calcular o valor total de desperdício para a categoria
    total_categoria = session.query(RegistroDesperdicio).filter_by(
        categoria_id=categoria_vencido.id
    ).with_entities(
        text("SUM(valor_estimado) as total")
    ).scalar()
    
    assert float(total_categoria) == 25.0
