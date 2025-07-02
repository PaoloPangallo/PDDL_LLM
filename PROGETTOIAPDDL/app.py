# app.py

# pylint: disable=missing-docstring,line-too-long,broad-except,unspecified-encoding

import os
import json
import logging
from flask import Flask, request, render_template, jsonify
from agents.reflection_agent import ask_local_llm
from core.utils import save_text_file
from routes import register_routes
from db.db import init_db


# 🔧 Configurazione Flask
app = Flask(__name__)
init_db()
UPLOAD_FOLDER = os.path.join(app.root_path, "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 🔧 Logging avanzato
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("questmaster.log", encoding="utf-8")
    ]
)
logging.getLogger().setLevel(logging.DEBUG)

@app.before_request
def log_request():
    app.logger.debug(
        "→ REQUEST %s %s args=%s form_keys=%s",
        request.method, request.path, dict(request.args), list(request.form.keys())
    )

@app.after_request
def log_response(response):
    app.logger.debug(
        "← RESPONSE %s %s status=%s",
        request.method, request.path, response.status_code
    )
    return response

# 🏠 Home
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# 🎯 Generazione diretta (fallback, legacy endpoint)
@app.route("/generate_action", methods=["POST"])
def generate_action():
    data = request.get_json()
    sentence = data.get("sentence", "").strip()
    session_id = data.get("session", "").strip()

    if not sentence:
        return jsonify(error="❌ Nessuna frase fornita."), 400

    prompt = (
        "Convertila in un'azione PDDL completa e ben formattata:\n"
        f'Frase: "{sentence}"\n'
        "Rispondi solo con l'azione PDDL, usando sintassi standard tipo:\n"
        "(:action attacca\n"
        " :parameters (?a - mago ?b - drago)\n"
        " :precondition (and (vivo ?a) (nemico ?b))\n"
        " :effect (not (vivo ?b)))"
    )

    try:
        action = ask_local_llm(prompt).strip()

        if session_id:
            session_dir = os.path.join(UPLOAD_FOLDER, session_id)
            os.makedirs(session_dir, exist_ok=True)
            save_text_file(os.path.join(session_dir, "natural_action.txt"), action)

            chat_path = os.path.join(session_dir, "chat_history.json")
            chat = []
            if os.path.exists(chat_path):
                with open(chat_path, "r", encoding="utf-8") as f:
                    chat = json.load(f)

            chat.append({"role": "user", "content": sentence})
            chat.append({"role": "assistant", "content": action})
            with open(chat_path, "w", encoding="utf-8") as f:
                json.dump(chat, f, ensure_ascii=False, indent=2)

        return jsonify(action=action)
    except Exception as e:
        app.logger.exception("❌ Errore nella generazione azione PDDL")
        return jsonify(error="❌ Errore durante la generazione."), 500

# ✅ Registra tutte le blueprint modulari
register_routes(app)

# 🚀 Avvio applicazione
if __name__ == "__main__":
    app.run(debug=False)


# Serve per FLASK_APP=app:app
application = app
