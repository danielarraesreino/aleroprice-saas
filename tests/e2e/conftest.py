import pytest
import os
from app import create_app, db
from app.models import *
from pytest_playwright.pytest_playwright import Page
import time
from datetime import datetime, timedelta

@pytest.fixture(scope='session')
def app_for_e2e():
    """Fixture que cria uma instu00e2ncia do aplicativo Flask para testes e2e"""
    app = create_app('testing')
    app.config['SERVER_NAME'] = 'localhost:5000'
    app.config['APPLICATION_ROOT'] = '/'
    
    with app.app_context():
        db.create_all()
        
        # Criamos alguns dados de teste para os cenu00e1rios e2e
        _criar_dados_teste(db.session)
        
        yield app
        
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
async def browser_context(browser, app_for_e2e):
    """Inicia o aplicativo Flask e configura o contexto do navegador para testes"""
    # Iniciar o servidor Flask em uma porta especu00edfica
    server = app_for_e2e.test_server()
    server.start()
    
    # Criar o contexto do navegador
    context = await browser.new_context()
    
    yield context
    
    # Limpar recursos apu00f3s o teste
    await context.close()
    server.stop()

@pytest.fixture(scope='function')
async def page(browser_context):
    """Cria uma nova página para cada teste"""
    page = await browser_context.new_page()
    yield page
    await page.close()

def _criar_dados_teste(session):
    """Cria dados de teste para os cenários e2e"""
    # Criar restaurante de teste
    from app.models.modelo_restaurante import Restaurante
    restaurant = Restaurante(
        nome="Restaurante E2E Teste",
        cnpj="11111111000100",
        telefone="19999999999"
    )
    session.add(restaurant)
    session.commit()
    
    # Criar fornecedor
    from app.models.modelo_fornecedor import Fornecedor
    fornecedor = Fornecedor(
        razao_social="Fornecedor E2E LTDA",
        cnpj="22222222000100",
        telefone="19888888888",
        restaurant_id=restaurant.id
    )
    session.add(fornecedor)
    session.commit()
    
    # Criar produtos para teste
    produtos = [
        Produto(
            nome="Arroz",
            descricao="Arroz branco tipo 1",
            unidade="kg",
            preco_unitario=5.0,  # Correct field name
            codigo="7891234567890",
            estoque_minimo=10,
            estoque_atual=50,
            fornecedor_id=fornecedor.id,
            restaurant_id=restaurant.id
        ),
        Produto(
            nome="Feijão",
            descricao="Feijão carioca",
            unidade="kg",
            preco_unitario=7.0,  # Correct field name
            codigo="7891234567891",
            estoque_minimo=8,
            estoque_atual=30,
            fornecedor_id=fornecedor.id,
            restaurant_id=restaurant.id
        ),
        Produto(
            nome="Óleo",
            descricao="Óleo de soja",
            unidade="un",
            preco_unitario=3.5,  # Correct field name
            codigo="7891234567892",
            estoque_minimo=12,
            estoque_atual=25,
            fornecedor_id=fornecedor.id,
            restaurant_id=restaurant.id
        )
    ]
    
    for produto in produtos:
        session.add(produto)
    session.commit()
    
    # Criar pratos
    from app.models.modelo_prato import Prato
    pratos = [
        Prato(
            nome="Arroz com Feijão",
            descricao="Prato tradicional",
            categoria="Pratos Principais",
            rendimento=1,
            preco_venda=15.00,
            restaurant_id=restaurant.id
        ),
        Prato(
            nome="Feijoada",
            descricao="Feijoada completa",
            categoria="Pratos Principais",
            rendimento=2,
            preco_venda=25.00,
            restaurant_id=restaurant.id
        )
    ]
    
    for prato in pratos:
        session.add(prato)
    session.commit()
    
    # Criar categorias de desperdício
    categorias = [
        CategoriaDesperdicio(nome="Vencido", descricao="Alimentos vencidos", cor="#FF0000"),
        CategoriaDesperdicio(nome="Sobra", descricao="Sobras de produção", cor="#FFA500"),
        CategoriaDesperdicio(nome="Dano", descricao="Alimentos danificados", cor="#FFFF00")
    ]
    
    for categoria in categorias:
        session.add(categoria)
    session.commit()
    
    # Criar histórico de vendas
    for prato in pratos:
        for i in range(30):  # 30 dias de histórico
            venda = HistoricoVendas(
                data=datetime.now().date() - timedelta(days=i),
                prato_id=prato.id,
                quantidade=10 + (i % 5),
                valor_total=(10 + (i % 5)) * prato.preco_venda,
                restaurant_id=restaurant.id
            )
            session.add(venda)
    
    # Criar alguns registros de desperdício
    for produto in produtos:
        for categoria in categorias:
            for i in range(5):  # 5 registros por combinação
                registro = RegistroDesperdicio(
                    categoria_id=categoria.id,
                    produto_id=produto.id,
                    quantidade=1.5 + (i % 3),
                    unidade=produto.unidade,
                    valor=(1.5 + (i % 3)) * float(produto.preco_unitario),
                    data_registro=datetime.now().date() - timedelta(days=i*2),
                    observacao=f"Registro de teste {i+1}",
                    restaurant_id=restaurant.id
                )
                session.add(registro)
    
    # Criar fatores de sazonalidade
    from app.models.modelo_previsao import FatorSazonalidade
    fatores = [
        FatorSazonalidade(
            tipo="dia_semana",
            nome="Segunda-feira",
            valor="segunda",
            fator=1.2,
            descricao="Segunda-feira",
            ativo=True,
            data_inicio=datetime.now().date(),
            data_fim=datetime.now().date() + timedelta(days=365)
        ),
        FatorSazonalidade(
            tipo="dia_semana",
            nome="Terça-feira",
            valor="terca",
            fator=0.9,
            descricao="Terça-feira",
            ativo=True,
            data_inicio=datetime.now().date(),
            data_fim=datetime.now().date() + timedelta(days=365)
        ),
        FatorSazonalidade(
            tipo="mes_ano",
            nome="Dezembro",
            valor="dezembro",
            fator=1.3,
            descricao="Dezembro",
            ativo=True,
            data_inicio=datetime.now().date(),
            data_fim=datetime.now().date() + timedelta(days=365)
        )
    ]
    
    for fator in fatores:
        session.add(fator)
    
    # Criar uma meta de redução de desperdício
    meta = MetaDesperdicio(
        categoria_id=categorias[0].id,
        produto_id=produtos[0].id,
        valor_inicial=500.0,
        valor_meta=400.0,
        percentual_reducao=20.0,
        data_inicio=datetime.now().date(),
        data_fim=datetime.now().date() + timedelta(days=30),
        descricao="Meta para redução de alimentos vencidos",
        restaurant_id=restaurant.id
    )
    session.add(meta)
    
    session.commit()
