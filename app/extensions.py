from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Criando a instância do SQLAlchemy
db = SQLAlchemy()

# Criando a instância de Migrate
migrate = Migrate()

# Adicione aqui outras extensões conforme necessário
from flask_login import LoginManager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'
login_manager.login_message_category = 'info'
