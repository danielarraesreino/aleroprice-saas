from flask import Blueprint

bp = Blueprint('campanha', __name__)

from app.routes.campanha import views  # noqa: E402,F401
