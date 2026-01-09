from flask import Blueprint

bp = Blueprint('public', __name__)

from app.routes.public import views
