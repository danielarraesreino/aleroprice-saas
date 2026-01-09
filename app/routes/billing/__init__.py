from flask import Blueprint

bp = Blueprint('billing', __name__)

from app.routes.billing import views
