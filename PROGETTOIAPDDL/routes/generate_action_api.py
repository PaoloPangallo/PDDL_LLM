# routes/generate_action_api.py

from flask import Blueprint, request, jsonify, current_app
import os, json
from agent.reflection_agent import ask_local_llm
from game.utils import save_text_file

generate_action_bp = Blueprint("generate_action_api", __name__)

@generate_action_bp.route("/generate_action", methods=["POST"])
def generate_action():
    data = request.get_json()
    sentence = data.get("sentence", "").strip()
    session_id = data.get("session", "").strip()

    if not sentence:
        return jsonify(error="❌ Nessuna frase fornita."), 400

    prompt = f"""Convertila in un'azione PDDL completa e ben formattata:
Frase: "{sentence}"
Rispondi solo con l'azione PDDL, usando sintassi standard tipo:
(:action attacca
 :parameters (?a - mago ?b - drago)
 :precondition (and (vivo ?a) (nemico ?b))
 :effect (not (vivo ?b)))"""

    try:
        action = ask_local_llm(prompt).strip()

        if session_id:
            session_dir = os.path.join("uploads", session_id)
            os.makedirs(session_dir, exist_ok=True)
            save_text_file(os.path.join(session_dir, "natural_action.txt"), action)

            # Aggiorna cronologia chat
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
        current_app.logger.exception("Errore nella generazione azione PDDL")
        return jsonify(error="❌ Errore durante la generazione."), 500
