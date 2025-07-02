# routes/__init__.py

# ✅ Importa tutti i blueprint dai moduli
from .core import core_bp
from .generate import generate_bp
from .result import result_bp
from .chat import chat_bp
from .refine import refine_bp
from .generate_action_api import generate_action_bp
from .extractor import extract_bp
from .pipeline import pipeline_bp
from .chat_bot import chatbot_bp  # blueprint chatbot con LangGraph

def register_routes(app):
    """Registra tutti i blueprint dell'applicazione Flask."""
    app.register_blueprint(core_bp)
    app.register_blueprint(generate_bp)
    app.register_blueprint(result_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(refine_bp)
    app.register_blueprint(generate_action_bp)
    app.register_blueprint(extract_bp)
    app.register_blueprint(pipeline_bp)
    app.register_blueprint(chatbot_bp, url_prefix="/api/chatbot")
