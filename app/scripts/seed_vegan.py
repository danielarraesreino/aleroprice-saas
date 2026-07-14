from app import db
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_produto import Produto
from app.models.modelo_prato import Prato, PratoInsumo
from app.models.modelo_fornecedor import Fornecedor
from app.models.modelo_cardapio import Cardapio, CardapioSecao, CardapioItem
from app.models.modelo_previsao import HistoricoVendas
# from faker import Faker
import random
import string
from datetime import datetime, timedelta, date

# fake = Faker('pt_BR')

def random_name():
    first = ["João", "Maria", "Pedro", "Ana", "Carlos", "Lucia", "Paulo", "Fernanda"]
    last = ["Silva", "Santos", "Oliveira", "Souza", "Lima", "Pereira", "Costa", "Almeida"]
    return f"{random.choice(first)} {random.choice(last)}"

def random_email(name):
    clean_name = name.lower().replace(' ', '.')
    domains = ["email.com", "teste.com", "vegan.com"]
    return f"{clean_name}@{random.choice(domains)}"

def random_phone():
    return f"(11) 9{random.randint(10000000, 99999999)}"

def seed_vegan_data():
    print("Iniciando seed de dados Veganos...")

    # 0. Criar o Restaurante (tenant). Todos os dados abaixo pertencem a ele.
    # O modelo é multi-tenant: Fornecedor/Produto/Prato/Cardapio/HistoricoVendas
    # exigem restaurant_id (NOT NULL).
    restaurante = Restaurante(nome="Restaurante Vegano (Seed)")
    db.session.add(restaurante)
    db.session.commit()
    restaurant_id = restaurante.id
    print(f"Restaurante seed criado (id={restaurant_id}).")

    # 1. Limpar dados existentes (opcional, pode comentar se quiser manter)
    # db.session.query(HistoricoVendas).delete()
    # db.session.query(CardapioItem).delete()
    # db.session.query(CardapioSecao).delete()
    # db.session.query(Cardapio).delete()
    # db.session.query(PratoInsumo).delete()
    # db.session.query(Prato).delete()
    # db.session.query(Produto).delete()
    # db.session.query(Fornecedor).delete()
    # db.session.commit()

    # 2. Criar Fornecedores Veganos
    fornecedores = []
    nomes_fornecedores = [
        "Horta Orgânica da Maria", "Fazenda Futuro", "Empório Natural", 
        "Zona Cerealista Atacado", "Cogumelos Mágicos Site", "Granja de Ovos (Fake) Plant Based"
    ]
    
    for i, nome_empresa in enumerate(nomes_fornecedores):
        contato = random_name()
        # Generate fake CNPJ
        fake_cnpj = f"{random.randint(10,99)}{random.randint(100,999)}{random.randint(100,999)}0001{random.randint(10,99)}"
        
        f = Fornecedor(
            razao_social=nome_empresa + " LTDA",
            nome_fantasia=nome_empresa,
            email=random_email(contato),
            telefone=random_phone(),
            cnpj=fake_cnpj,
            restaurant_id=restaurant_id
        )
        db.session.add(f)
        fornecedores.append(f)
    db.session.commit()
    print("Fornecedores criados.")

    # 3. Criar Produtos (Ingredientes)
    ingredientes = [
        # Nome, Preço Unit, Unidade
        ("Jaca Verde", 15.00, "kg"), ("Grão de Bico", 10.00, "kg"), ("Tofu Defumado", 45.00, "kg"),
        ("Cogumelo Shimeji", 35.00, "kg"), ("Leite de Coco", 12.00, "L"), ("Aveia em Flocos", 8.00, "kg"),
        ("Seitan (Glúten)", 25.00, "kg"), ("Banana da Terra", 6.00, "kg"), ("Arroz Integral", 5.00, "kg"),
        ("Lentilha", 12.00, "kg"), ("Batata Doce", 4.00, "kg"), ("Mandioquinha", 8.00, "kg"),
        ("Couve Manteiga", 3.00, "maço"), ("Alho Poró", 5.00, "un"), ("Tomate Italiano", 7.00, "kg"),
        ("Cebola Roxa", 6.00, "kg"), ("Alho", 30.00, "kg"), ("Azeite de Oliva", 40.00, "L"),
        ("Castanha de Caju", 90.00, "kg"), ("Levedura Nutricional", 120.00, "kg"),
        ("Fumaça Líquida", 50.00, "L"), ("Páprica Defumada", 60.00, "kg"), ("Curry Indiano", 55.00, "kg"),
        ("Chia", 40.00, "kg"), ("Linhaça Dourada", 20.00, "kg")
    ]
    
    objs_produtos = []
    for nome, preco, unidade in ingredientes:
        p = Produto(
            codigo=str(random.randint(10000, 99999)),
            nome=nome,
            preco_unitario=preco,
            unidade=unidade,
            estoque_atual=random.uniform(5, 50),
            estoque_minimo=5,
            fornecedor_id=random.choice(fornecedores).id,
            ativo=True,
            restaurant_id=restaurant_id
        )
        db.session.add(p)
        objs_produtos.append(p)
    db.session.commit()
    print("Ingredientes criados.")

    # 4. Criar Pratos (30 Itens)
    cardapio_vegan = Cardapio(nome="Menu Vegano Especial", ativo=True, restaurant_id=restaurant_id)
    db.session.add(cardapio_vegan)
    db.session.commit()

    secoes = ["Entradas", "Principais", "Sobremesas", "Bebidas"]
    objs_secoes = {}
    for s in secoes:
        sec = CardapioSecao(nome=s, cardapio_id=cardapio_vegan.id, ordem=secoes.index(s))
        db.session.add(sec)
        objs_secoes[s] = sec
    db.session.commit()

    lista_pratos = [
        # Nome, Custo, Preço Venda, Categoria, Seção
        ("Coxinha de Jaca", 3.50, 12.00, "Salgados", "Entradas"),
        ("Falafel Assado", 2.00, 18.00, "Salgados", "Entradas"),
        ("Dadinho de Tapioca", 4.00, 22.00, "Petiscos", "Entradas"),
        ("Bruschetta de Cogumelos", 5.50, 24.00, "Petiscos", "Entradas"),
        ("Salada Caprese Vegana (Tofu)", 6.00, 28.00, "Saladas", "Entradas"),
        ("Ceviche de Banana da Terra", 4.50, 25.00, "Saladas", "Entradas"),
        ("Guacamole com Totopos", 5.00, 26.00, "Petiscos", "Entradas"),
        ("Carpaccio de Abobrinha", 3.00, 20.00, "Saladas", "Entradas"),
        
        ("Moqueca de Banana da Terra", 12.00, 45.00, "Pratos Principais", "Principais"),
        ("Bobó de Cogumelos", 14.00, 48.00, "Pratos Principais", "Principais"),
        ("Feijoada Vegana (Defumada)", 10.00, 39.00, "Brasileiro", "Principais"),
        ("Strogonoff de Grão de Bico", 8.00, 35.00, "Clássicos", "Principais"),
        ("Risoto de Funghi Secchi", 11.00, 42.00, "Italiano", "Principais"),
        ("Lasanha de Berinjela", 10.50, 40.00, "Italiano", "Principais"),
        ("Burger 'Futuro' Caseiro", 9.00, 38.00, "Lanches", "Principais"),
        ("Poke Bowl com Tofu Grelhado", 13.00, 44.00, "Asiático", "Principais"),
        ("Yakisoba de Legumes", 7.00, 32.00, "Asiático", "Principais"),
        ("Curry de Grão de Bico Indiano", 8.50, 36.00, "Indiano", "Principais"),
        ("Escondidinho de Seitan", 11.50, 41.00, "Brasileiro", "Principais"),
        ("Mac'n'Cheese Vegano (Castanha)", 15.00, 46.00, "Americano", "Principais"),
        
        ("Cheesecake de Frutas Vermelhas", 8.00, 22.00, "Doces", "Sobremesas"),
        ("Brownie de Feijão Preto (Fit)", 4.00, 18.00, "Doces", "Sobremesas"),
        ("Mousse de Chocolate com Abacate", 5.00, 16.00, "Doces", "Sobremesas"),
        ("Torta de Limão Crua", 7.00, 20.00, "Doces", "Sobremesas"),
        ("Sorvete de Banana e Cacau", 2.00, 14.00, "Doces", "Sobremesas"),
        ("Pudim de Chia com Manga", 3.50, 15.00, "Doces", "Sobremesas"),
        
        ("Suco Verde Detox", 2.50, 12.00, "Bebidas", "Bebidas"),
        ("Kombucha da Casa", 3.00, 15.00, "Bebidas", "Bebidas"),
        ("Smoothie de Frutas", 4.00, 16.00, "Bebidas", "Bebidas"),
        ("Chá Mate Gelado", 1.00, 8.00, "Bebidas", "Bebidas")
    ]

    pratos_objs = []
    
    for nome, custo, venda, categ, secao_nome in lista_pratos:
        p = Prato(
            nome=nome,
            descricao=f"Delicioso prato vegano {nome}, feito com ingredientes selecionados.",
            # modo_preparo removed
            tempo_preparo=random.randint(15, 60),
            rendimento=1,
            unidade_rendimento="porção", # Required field
            porcoes_rendimento=1, # Required field
            # custo_total removed (it's a property based on ingredients)
            categoria=categ,
            preco_venda=venda, # Explicitly setting selling price
            restaurant_id=restaurant_id
        )
        db.session.add(p)
        db.session.commit() # Commit to get ID

        # Associar alguns ingredientes aleatórios
        num_insumos = random.randint(2, 5)
        insumos_usados = random.sample(objs_produtos, num_insumos)
        for ing in insumos_usados:
            pi = PratoInsumo(
                prato_id=p.id,
                produto_id=ing.id,
                quantidade=random.uniform(0.1, 0.5), # Kgs
                # custo_calculado removed (not in model)
            )
            db.session.add(pi)
        
        # Criar item no cardápio
        item_cardapio = CardapioItem(
            secao_id=objs_secoes[secao_nome].id,
            prato_id=p.id,
            # nome, descricao removed (they belong to Prato)
            preco_venda=venda,
            # preco_custo removed (not in model)
            disponivel=True # Replaces ativo
        )
        db.session.add(item_cardapio)
        pratos_objs.append((p, item_cardapio))
    
    db.session.commit()
    print("Pratos e Cardápio criados.")

    # 5. Simular Vendas (Últimos 30 dias)
    print("Simulando histórico de vendas...")
    data_hoje = date.today()
    vendas_buffer = []
    
    for dias_atras in range(30):
        data_venda = data_hoje - timedelta(days=dias_atras)
        
        # Sazonalidade (Fim de semana vende mais)
        eh_fds = data_venda.weekday() >= 5
        num_pedidos = random.randint(20, 50) if eh_fds else random.randint(10, 25)
        
        for _ in range(num_pedidos):
            prato, item_cardapio = random.choice(pratos_objs)
            qtd = random.randint(1, 3)
            valor_venda = float(item_cardapio.preco_venda) * qtd
            
            venda = HistoricoVendas(
                data=data_venda,
                cardapio_item_id=item_cardapio.id,
                prato_id=prato.id,
                quantidade=qtd,
                valor_unitario=item_cardapio.preco_venda,
                valor_total=valor_venda,
                periodo_dia=random.choice(['Almoço', 'Jantar']),
                dia_semana=data_venda.weekday(), # Integer 0-6
                mes=data_venda.month,
                semana_mes=(data_venda.day - 1) // 7 + 1,
                # ano removed (not in model)
                restaurant_id=restaurant_id
            )
            vendas_buffer.append(venda)
            # Commit em lotes para não sobrecarregar
            if len(vendas_buffer) >= 100:
                db.session.add_all(vendas_buffer)
                db.session.commit()
                vendas_buffer = []

    if vendas_buffer:
        db.session.add_all(vendas_buffer)
        db.session.commit()
        
    print("Vendas simuladas com sucesso!")
    return "Dados Veganos Preenchidos com Sucesso! 30 Pratos criados e vendas simuladas."

if __name__ == '__main__':
    from app import create_app, db
    app = create_app()
    with app.app_context():
        seed_vegan_data()
