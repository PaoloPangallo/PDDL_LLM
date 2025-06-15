import os

BASE_DIR = "routes"
FILES = {
    "__init__.py": '''# Inizializza i blueprint delle route

from .core import core_bp
from .generate import generate_bp
from .result import result_bp
from .chat import chat_bp
from .refine import refine_bp

def register_routes(app):
    app.register_blueprint(core_bp)
    app.register_blueprint(generate_bp)
    app.register_blueprint(result_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(refine_bp)
''',

    "core.py": '''from flask import Blueprint, render_template, send_file, abort, request
import os
from werkzeug.utils import secure_filename

core_bp = Blueprint("core", __name__)

@core_bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@core_bp.route("/uploads/<session>/<filename>")
def download_file(session, filename):
    if ".." in filename or filename.startswith("/"):
        abort(400, "Nome file non valido.")
    folder = os.path.join(core_bp.root_path, "..", "uploads", session)
    file_path = os.path.join(folder, secure_filename(filename))
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=filename)
    abort(404, f"File non trovato: {filename}")

@core_bp.app_errorhandler(500)
def internal_error(e):
    core_bp.logger.error(f"500 Internal Server Error: {e}")
    return "❌ Errore interno del server. Controlla i log per maggiori dettagli.", 500
''',

    "generate.py": '''from flask import Blueprint

generate_bp = Blueprint("generate", __name__)

# Aggiungi qui la route /generate
''',

    "result.py": '''from flask import Blueprint

result_bp = Blueprint("result", __name__)

# Aggiungi qui la route /result
''',

    "chat.py": '''from flask import Blueprint

chat_bp = Blueprint("chat", __name__)

# Aggiungi qui le route /chat e /generate_action
''',

    "refine.py": '''from flask import Blueprint

refine_bp = Blueprint("refine", __name__)

# Aggiungi qui la route /regenerate
'''
}


def create_structure():
    os.makedirs(BASE_DIR, exist_ok=True)
    for filename, content in FILES.items():
        path = os.path.join(BASE_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        print(f"✅ Creato: {path}")


if __name__ == "__main__":
    create_structure()
