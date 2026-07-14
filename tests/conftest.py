import os
import sys
import pytest
from flask import Flask

# Adicionar o diretório raiz do projeto ao PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import *

@pytest.fixture(scope='session')
def app():
    """
    Fixture que cria uma instância do aplicativo Flask para testes
    """
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    """
    Cliente de teste. O test_client gerencia o contexto de app/request por
    requisição — não embrulhar em test_request_context() manual (causava
    'Working outside of request context' no teardown).
    """
    return app.test_client()

@pytest.fixture(scope='session')
def runner(app):
    """
    Fixture que cria um executor de comandos CLI para o aplicativo Flask
    """
    return app.test_cli_runner()

@pytest.fixture(scope='function')
def session(app):
    """
    Fixture que cria uma sessão de banco de dados para testes
    com gerenciamento adequado de transações para isolar cada teste
    """
    with app.app_context():
        # Configurar conexão isolada para cada teste
        connection = db.engine.connect()
        transaction = connection.begin()
        
        # Configurar a sessão para usar esta conexão
        session = db.scoped_session(
            db.sessionmaker(autocommit=False, autoflush=False, bind=connection)
        )
        original_session = db.session
        db.session = session

        yield session

        # Limpar após cada teste e restaurar db.session para não contaminar
        # os próximos testes (que usam client sem a fixture session).
        session.close()
        transaction.rollback()
        connection.close()
        db.session = original_session

@pytest.fixture
def restaurant(session):
    """Create a test restaurant"""
    from app.models.modelo_restaurante import Restaurante
    restaurant = Restaurante(
        nome="Restaurante Teste",
        cnpj="12345678000190",
        telefone="19999999999"
    )
    session.add(restaurant)
    session.commit()
    return restaurant

@pytest.fixture
def fornecedor(session, restaurant):
    """Create a test supplier"""
    from app.models.modelo_fornecedor import Fornecedor
    fornecedor = Fornecedor(
        razao_social="Fornecedor Teste LTDA",
        cnpj="98765432000100",
        telefone="19888888888",
        restaurant_id=restaurant.id
    )
    session.add(fornecedor)
    session.commit()
    return fornecedor

@pytest.fixture
def produto(session, restaurant, fornecedor):
    """Create a test product with correct field names"""
    from app.models.modelo_produto import Produto
    produto = Produto(
        nome="Arroz",
        descricao="Arroz branco tipo 1",
        unidade="kg",
        preco_unitario=5.50,  # Correct field name
        estoque_minimo=10.0,
        estoque_atual=50.0,
        categoria="Grãos",
        fornecedor_id=fornecedor.id,
        restaurant_id=restaurant.id
    )
    session.add(produto)
    session.commit()
    return produto

@pytest.fixture
def prato(session, restaurant):
    """Create a test dish"""
    from app.models.modelo_prato import Prato
    prato = Prato(
        nome="Arroz com Feijão",
        descricao="Prato tradicional brasileiro",
        categoria="Pratos Principais",
        rendimento=1,  # Required field
        unidade_rendimento="kg",  # Required (NOT NULL)
        porcoes_rendimento=1,     # Required (NOT NULL)
        preco_venda=15.00,
        restaurant_id=restaurant.id
    )
    session.add(prato)
    session.commit()
    return prato


@pytest.fixture
def auth_client(client, session, restaurant):
    """Cliente de teste autenticado como admin do restaurante de teste.
    Necessário para rotas de negócio, que agora exigem login (before_request)."""
    from app.models.usuario import Usuario
    user = Usuario(
        nome="Admin Teste",
        email="admin.teste@bardavila.com",
        senha="SenhaTeste123",
        tipo="admin",
        restaurant_id=restaurant.id,
    )
    session.add(user)
    session.commit()
    resp = client.post(
        '/auth/login',
        data={'email': 'admin.teste@bardavila.com', 'senha': 'SenhaTeste123'},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 200), f"login falhou: {resp.status_code}"
    return client
