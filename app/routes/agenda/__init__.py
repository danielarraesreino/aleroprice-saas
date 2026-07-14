from flask import Blueprint

bp = Blueprint('agenda', __name__)

from app.routes.agenda import views  # noqa: E402,F401
