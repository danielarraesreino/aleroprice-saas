from flask import Blueprint

bp = Blueprint('agentes', __name__, url_prefix='/agentes')

from . import views  # noqa: E402, F401
