from flask import Blueprint

bp = Blueprint('configsite', __name__)

from app.routes.configsite import views  # noqa: E402,F401
