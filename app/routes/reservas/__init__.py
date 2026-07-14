from flask import Blueprint

bp = Blueprint('reservas', __name__)

from app.routes.reservas import views  # noqa: E402,F401
