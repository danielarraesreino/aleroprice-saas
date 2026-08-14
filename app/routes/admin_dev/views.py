"""Rotas de manutenção de desenvolvimento. Só existem quando o blueprint é
registrado (ver `__init__.registrar`) — nunca em produção.

Toda rota exige `?token=$ADMIN_DEV_TOKEN`. Token errado responde 404, não 403:
o endpoint não se anuncia para quem não deveria saber que ele existe.
"""
import hmac
import os

from flask import abort, jsonify, request

from app.extensions import db
from app.routes.admin_dev import bp


def _exige_token():
    esperado = os.environ.get('ADMIN_DEV_TOKEN') or ''
    recebido = request.args.get('token') or ''
    if not esperado or not hmac.compare_digest(recebido, esperado):
        abort(404)


@bp.before_request
def _porteiro():
    _exige_token()


@bp.route('/db', strict_slashes=False)
def inspecionar_db():
    """Diagnóstico: tabelas, versão do Alembic e host do banco (sem credencial)."""
    from flask import current_app
    from sqlalchemy import inspect, text

    try:
        inspetor = inspect(db.engine)
        try:
            versao = db.session.execute(text('SELECT version_num FROM alembic_version')).scalar()
        except Exception:
            db.session.rollback()
            versao = None

        uri = current_app.config.get('SQLALCHEMY_DATABASE_URI') or ''
        return jsonify({
            'status': 'online',
            'tabelas': sorted(inspetor.get_table_names()),
            'alembic_version': versao,
            # Só a parte depois do '@': nunca devolver usuário e senha.
            'banco': uri.split('@')[-1] if '@' in uri else uri.split('///')[-1],
        })
    except Exception as e:
        return jsonify({'erro': f'{type(e).__name__}: {e}'}), 500


@bp.route('/seed-vegan', strict_slashes=False)
def seed_vegan():
    """Popula o banco de dev com o restaurante vegano de demonstração."""
    try:
        from app.scripts.seed_vegan import seed_vegan_data
        return jsonify({'status': 'ok', 'mensagem': seed_vegan_data()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'erro': f'{type(e).__name__}: {e}'}), 500


@bp.route('/reset-db', methods=['POST'], strict_slashes=False)
def reset_db():
    """APAGA TODAS AS TABELAS e recria o schema vazio.

    Só POST e com dupla confirmação (`?confirmar=APAGAR-TUDO`): um GET com o
    token vazando num histórico de navegador não pode destruir um banco.
    """
    if request.args.get('confirmar') != 'APAGAR-TUDO':
        return jsonify({
            'status': 'recusado',
            'motivo': 'faltou confirmar=APAGAR-TUDO',
            'aviso': 'Esta rota apaga todas as tabelas do banco atual.',
        }), 400
    try:
        db.drop_all()
        db.create_all()
        return jsonify({'status': 'ok', 'mensagem': 'schema recriado vazio'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'erro': f'{type(e).__name__}: {e}'}), 500
