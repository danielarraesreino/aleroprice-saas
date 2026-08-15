from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import MetaData

# Nomes previsíveis para constraints e índices.
#
# Sem isto, o SQLite cria constraint anônima — e `batch_alter_table` não
# consegue dropar o que não tem nome, o que trava qualquer migration futura de
# unique/check. O Postgres já nomeava sozinho (`pratos_nome_key`), então isto
# alinha os dois ambientes.
#
# Convenção só vale para objetos criados DEPOIS daqui; o que já existe em
# produção mantém o nome antigo. Por isso as migrations descobrem o nome real
# por reflexão em vez de assumir.
CONVENCAO_DE_NOMES = {
    'ix': 'ix_%(column_0_label)s',
    'uq': 'uq_%(table_name)s_%(column_0_name)s',
    'ck': 'ck_%(table_name)s_%(constraint_name)s',
    'fk': 'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s',
    'pk': 'pk_%(table_name)s',
}

# Criando a instância do SQLAlchemy
db = SQLAlchemy(metadata=MetaData(naming_convention=CONVENCAO_DE_NOMES))

# Criando a instância de Migrate
migrate = Migrate()

# Proteção CSRF de todo POST/PUT/PATCH/DELETE.
#
# Ligada em `create_app`. Três endpoints ficam de fora, e cada um por um motivo
# diferente (ver os `csrf.exempt` correspondentes):
#   - billing.webhook  → o Stripe chama de fora, sem sessão; a autenticação
#                        dele é a assinatura HMAC do payload, não o cookie.
#   - bootstrap_demo   → manutenção via curl, gated por SEED_TOKEN.
# Todo o resto — inclusive `public.reservar`, que é POST anônimo de site
# público — exige token. O formulário de reserva manda o token no corpo
# (input hidden dentro do <form>, que o FormData carrega) e no header
# X-CSRFToken.
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()

# Adicione aqui outras extensões conforme necessário
from flask_login import LoginManager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'
login_manager.login_message_category = 'info'
