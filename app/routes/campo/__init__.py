from flask import Blueprint

bp = Blueprint('campo', __name__)

from app.routes.campo import views  # noqa: E402,F401
