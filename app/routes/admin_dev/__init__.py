"""Ferramentas destrutivas de desenvolvimento.

Isolado num blueprint próprio porque `/reset-db` chama `db.drop_all()` — em
produção isso apagaria todos os tenants. Ficando solto no `run.py`, a proteção
dependia de alguém ler um `if` no meio do arquivo de boot.

Regras de registro (ver `registrar`):

1. só existe com `ENABLE_ADMIN_ENDPOINTS=1` explícito;
2. **nunca** em produção — e a tentativa levanta erro no boot em vez de
   ignorar em silêncio, para que a configuração errada apareça no deploy e
   não meses depois;
3. exige `ADMIN_DEV_TOKEN` e compara em tempo constante.

Endpoints ficam sob `/admin-dev/`, fora do espaço de URL da aplicação.
"""
from flask import Blueprint

bp = Blueprint('admin_dev', __name__)

from app.routes.admin_dev import views  # noqa: E402,F401


class ConfiguracaoInsegura(RuntimeError):
    """Tentativa de habilitar ferramenta destrutiva em produção."""


def registrar(app, config_name):
    """Registra o blueprint só quando é seguro. Devolve True se registrou."""
    import os

    habilitado = os.environ.get('ENABLE_ADMIN_ENDPOINTS') == '1'
    if not habilitado:
        return False

    if config_name == 'production':
        raise ConfiguracaoInsegura(
            'ENABLE_ADMIN_ENDPOINTS=1 com APP_ENV=production. Estas rotas apagam '
            'o banco (db.drop_all). Remova a variável do ambiente de produção.'
        )

    if not os.environ.get('ADMIN_DEV_TOKEN'):
        raise ConfiguracaoInsegura(
            'ENABLE_ADMIN_ENDPOINTS=1 exige ADMIN_DEV_TOKEN definido.'
        )

    app.register_blueprint(bp, url_prefix='/admin-dev')
    app.logger.warning(
        'ROTAS DESTRUTIVAS ATIVAS em /admin-dev (ENABLE_ADMIN_ENDPOINTS=1). '
        'Nunca use esta configuração em produção.'
    )
    return True
