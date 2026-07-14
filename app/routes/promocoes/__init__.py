from flask import Blueprint

bp = Blueprint('promocoes', __name__)

from app.routes.promocoes import views  # noqa: E402,F401
