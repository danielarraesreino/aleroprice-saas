import os
from datetime import timedelta

class Config:
    """Configuração base da aplicação"""
    # Configuração do Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'uma-chave-secreta-dificil-de-adivinhar'
    
    # Configuração do SQLAlchemy
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///alerodb.sqlite'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configurações padrão
    ESTOQUE_ALERTA_PERCENTUAL = 0.2  # Alerta quando estoque < 20% do mínimo
    MARGEM_LUCRO_PADRAO = 30  # Margem padrão de 30%
    RATEIO_CUSTOS_METODO = 'proporcional'  # Método de rateio de custos indiretos
    
    # Configurações de token (se expandir para API)
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

class DevelopmentConfig(Config):
    """Configuração de desenvolvimento"""
    DEBUG = True
    SQLALCHEMY_ECHO = True

class TestingConfig(Config):
    """Configuração de testes"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """Configuração de produção"""
    DEBUG = False
    # Use variáveis de ambiente em produção
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    # Prevent SQLite in production to avoid Read-Only FS errors
    if not SQLALCHEMY_DATABASE_URI:
        # Fallback to in-memory SQLite if no DB provided (just to allow boot, data will be lost)
        # Or better: don't set a default that writes to disk
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)

# Dicionário com as configurações disponíveis
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
