"""Route Flask per gestire le interazioni chat con Ollama, usando i file PDDL generati."""

import os
import json
from flask import Blueprint, request, jsonify, current_app
from game.utils import ask_ollama, read_text_file

chat_bp = Blueprint("chat", __name__)


def chat_with_ollama():
    """Gestisce la conversazione utente con Ollama basandosi su PDDL + validazione."""
    data = request.get_json()
    session_id = data.get("session")
    user_message = data.get("message")

    session_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], session_id)
    domain_path = os.path.join(session_dir, "domain.pddl")
    problem_path = os.path.join(session_dir, "problem.pddl")
    validation_path = os.path.join(session_dir, "validation.json")
    chat_history_path = os.path.join(session_dir, "chat_history.json")

    if not all(os.path.exists(p) for p in [domain_path, problem_path]):
        return jsonify({"error": "File PDDL mancanti"}), 400

    domain = read_text_file(domain_path)
    problem = read_text_file(problem_path)

    # Ricostruzione sommario di validazione
    validation_summary = ""
    if os.path.exists(validation_path):
        try:
            with open(validation_path, encoding="utf-8") as f:
                validation = json.load(f)
            if not validation.get("valid_syntax", True):
                missing = validation.get("missing_sections", [])
                undefined_objs = validation.get("undefined_objects_in_goal", [])
                undefined_acts = validation.get("undefined_actions", [])
                validation_summary = (
                    "⚠️ Il file PDDL non è valido.\n"
                    f"- Sezioni mancanti: {', '.join(missing) if missing else 'nessuna'}\n"
                    f"- Oggetti non definiti nel goal: "
                    f"{', '.join(undefined_objs) if undefined_objs else 'nessuno'}\n"
                    f"- Azioni non definite: "
                    f"{', '.join(undefined_acts) if undefined_acts else 'nessuna'}"
                )
        except (json.JSONDecodeError, OSError) as e:
            current_app.logger.warning("⚠️ Errore nel parsing di validation.json: %s", e)

    # Costruzione messaggio di contesto
    system_message = (
        "Questi sono i file PDDL correnti:\n\n"
        f"=== DOMAIN START ===\n{domain}\n=== DOMAIN END ===\n\n"
        f"=== PROBLEM START ===\n{problem}\n=== PROBLEM END ===\n\n"
        f"{validation_summary if validation_summary else '✅ I file sembrano sintatticamente corretti.'}\n"
    )

    # Caricamento chat precedente
    chat_history = []
    if os.path.exists(chat_history_path):
        try:
            with open(chat_history_path, encoding="utf-8") as f:
                chat_history = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            current_app.logger.warning("⚠️ Errore nel parsing di chat_history.json: %s", e)
    if not chat_history:
        chat_history = [{"role": "system", "content": system_message}]

    # Aggiunta nuovo messaggio utente
    chat_history.append({"role": "user", "content": user_message})

    # Costruzione del prompt per Ollama
    prompt = ""
    for msg in chat_history:
        if msg["role"] == "system":
            prompt += f"📚 Contesto iniziale:\n{msg['content']}\n\n"
        elif msg["role"] == "user":
            prompt += f"👤 Utente: {msg['content']}\n"
        elif msg["role"] == "assistant":
            prompt += f"🤖 Assistente: {msg['content']}\n"

    try:
        reply = ask_ollama(prompt)
        chat_history.append({"role": "assistant", "content": reply})

        with open(chat_history_path, "w", encoding="utf-8") as f:
            json.dump(chat_history, f, indent=2, ensure_ascii=False)

        return jsonify({"reply": reply})
    except Exception as e:
        current_app.logger.error("❌ Errore Ollama: %s", e)
        return jsonify({"error": str(e)}), 500
