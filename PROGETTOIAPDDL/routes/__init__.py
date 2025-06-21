# routes/__init__.py

from .core import core_bp
from .generate import generate_bp
from .result import result_bp
from .chat import chat_bp
from .refine import refine_bp
from .generate_action_api import generate_action_bp  # 🧠 API JSON
from .extractor import extract_bp


def register_routes(app):
    app.register_blueprint(core_bp)
    app.register_blueprint(generate_bp)
    app.register_blueprint(result_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(refine_bp)
    app.register_blueprint(generate_action_bp)  # 🧠 API JSON
    app.register_blueprint(extract_bp)          # 🌐 Pagina HTML
