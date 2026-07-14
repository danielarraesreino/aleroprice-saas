from flask import Blueprint

bp = Blueprint('conteudo', __name__)

from app.routes.conteudo import views  # noqa: E402,F401
