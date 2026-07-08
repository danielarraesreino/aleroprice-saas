import pytest
from datetime import datetime, timedelta
from app.models.modelo_desperdicio import CategoriaDesperdicio
from app.models.modelo_produto import Produto

def test_app_exists(app):
    """Verifica se a aplicau00e7u00e3o Flask foi criada corretamente"""
    assert app is not None

def test_app_is_testing(app):
    """Verifica se a aplicau00e7u00e3o estu00e1 em modo de teste"""
    assert app.config['TESTING']

def test_db_connection(app):
    """Verifica a conexu00e3o com o banco de dados"""
    from app import db
    from sqlalchemy import text
    
    with app.app_context():
        # Verifica se o engine do SQLAlchemy estu00e1 funcionando
        assert db.engine is not None
        
        # Executa uma consulta simples para confirmar que o banco estu00e1 funcionando
        result = db.session.execute(text("SELECT 1")).scalar()
        assert result == 1

def test_categoria_desperdicio_create(session, restaurant):
    """Testa a criau00e7u00e3o de uma categoria de desperdu00edcio"""
    # Criar uma categoria de teste
    categoria = CategoriaDesperdicio(
        nome="Categoria de Teste", 
        descricao="Categoria criada para teste", 
        cor="#FF5733",
        restaurant_id=restaurant.id
    )
    session.add(categoria)
    session.commit()
    
    # Verificar se a categoria foi criada corretamente
    assert categoria.id is not None
    assert categoria.nome == "Categoria de Teste"
    assert categoria.descricao == "Categoria criada para teste"
    assert categoria.cor == "#FF5733"
    
    # Verificar se a categoria pode ser recuperada do banco
    categoria_db = session.query(CategoriaDesperdicio).filter_by(id=categoria.id).first()
    assert categoria_db is not None
    assert categoria_db.nome == categoria.nome

def test_produto_create(session, restaurant, fornecedor):
    """Testa a criau00e7u00e3o de um produto"""
    # Criar um produto de teste
    produto = Produto(
        nome="Produto de Teste",
        descricao="Produto criado para teste",
        unidade="kg",
        preco_unitario=10.50,
        estoque_minimo=5.0,
        estoque_atual=15.0,
        categoria="Testes",
        fornecedor_id=fornecedor.id,
        restaurant_id=restaurant.id
    )
    session.add(produto)
    session.commit()
    
    # Verificar se o produto foi criado corretamente
    assert produto.id is not None
    assert produto.nome == "Produto de Teste"
    assert produto.descricao == "Produto criado para teste"
    assert produto.unidade == "kg"
    assert float(produto.preco_unitario) == 10.50
    assert produto.estoque_atual == 15.0
    
    # Verificar se o produto pode ser recuperado do banco
    produto_db = session.query(Produto).filter_by(id=produto.id).first()
    assert produto_db is not None
    assert produto_db.nome == produto.nome
