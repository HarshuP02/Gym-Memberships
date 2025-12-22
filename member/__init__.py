from flask import Blueprint

member_bp = Blueprint("member", __name__)
from member import routes
