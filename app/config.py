import os
from datetime import timedelta

from dotenv import load_dotenv

# Carrega as chaves do .env (gitignorado) antes das classes abaixo lerem os
# os.environ.get(...). Caminho explícito até a raiz do projeto.
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

class Config:
    """Configuração base da aplicação"""
    # Configuração do Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'uma-chave-secreta-dificil-de-adivinhar'
    
    # Configuração do SQLAlchemy
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///alerodb.sqlite'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Gestão de custos/estoque/NF-e/previsão desligada por padrão: o produto
    # vendido é o site + o admin do site. Ligada, ela também precisa das
    # dependências de requirements-gestao.txt (pandas, numpy...). Avaliação que
    # motivou desligar: docs/AVALIACAO_GESTAO_2026-10.md.
    GESTAO_ATIVA = os.environ.get('GESTAO_ATIVA') == '1'
    
    # Configurações padrão
    ESTOQUE_ALERTA_PERCENTUAL = 0.2  # Alerta quando estoque < 20% do mínimo
    MARGEM_LUCRO_PADRAO = 30  # Margem padrão de 30%
    RATEIO_CUSTOS_METODO = 'proporcional'  # Método de rateio de custos indiretos
    
    # Configurações de token (se expandir para API)
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

    # Sessão. O uso real é o celular numa visita: sair pra câmera ou pro
    # WhatsApp e voltar não pode deslogar. Sem REMEMBER_COOKIE_DURATION o
    # cookie de sessão morre junto com a aba.
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # CSRF (flask-wtf, ligado em `create_app`).
    #
    # Token vale enquanto a sessão valer, em vez de expirar em 1h (padrão do
    # flask-wtf). Os dois usos reais aqui são páginas que ficam abertas: o site
    # do bar no celular de quem vai reservar, e a tela do Modo Campo durante a
    # visita inteira. Com o limite de 1h, voltar pra aba depois do almoço fazia
    # a reserva e o upload de foto morrerem em 400 sem explicação. Expirar
    # junto com a sessão mantém a garantia que importa (token amarrado a uma
    # sessão específica) sem esse falso negativo.
    WTF_CSRF_TIME_LIMIT = None

class DevelopmentConfig(Config):
    """Configuração de desenvolvimento"""
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True
    SQLALCHEMY_ECHO = True

class TestingConfig(Config):
    """Configuração de testes"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    # A suíte existente cobre a gestão; o produto só-site tem a config abaixo.
    GESTAO_ATIVA = True


class TestingSiteConfig(TestingConfig):
    """Testes do produto como roda em produção: sem a gestão."""
    GESTAO_ATIVA = False

class ProductionConfig(Config):
    """Configuração de produção"""
    DEBUG = False

    # Um dia de cache nos arquivos servidos pelo Flask.
    #
    # O `vercel.json` faz rewrite de TUDO para a função Python — inclusive
    # `/static` —, então cada capa de bar (até 250 KB) era servida pelo Flask
    # com `no-cache` e rebaixada a cada visita. Quem abre o site do bar no 4G
    # pagava o download de novo toda vez, e a função rodava para devolver um
    # arquivo que não muda.
    SEND_FILE_MAX_AGE_DEFAULT = 86400

    # Segredos e banco são exigidos em produção — a checagem (fail fast) acontece
    # no create_app, não aqui, para não quebrar o import do módulo em dev/teste.
    SECRET_KEY = os.environ.get('SECRET_KEY')

    # HTTPS em produção: cookie de sessão e de "continuar conectado" só viajam
    # cifrados. Fora daqui fica desligado, senão o login quebra em dev (http).
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)

    # O Postgres gerenciado derruba conexão ociosa (e o compute dorme). A função
    # serverless reaproveita a conexão do pool entre requisições e a primeira
    # consulta depois da pausa morria com "SSL connection has been closed
    # unexpectedly" — 500 na home e no /bar/<slug>. pre_ping testa antes de usar
    # e reabre; recycle descarta conexão velha antes do servidor matá-la.
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True, 'pool_recycle': 280}

# Dicionário com as configurações disponíveis
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'testing_site': TestingSiteConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
