"""Blueprint conversazionale per chatbot PDDL con memoria persistente."""
import os
import json
import logging
from flask import Blueprint, request, jsonify
from langchain_core.messages import HumanMessage
from langgraph.graph.message import add_messages
from graphs.pddl_pipeline_graph import get_pipeline_with_memory

URL_PREFIX = "/api/chatbot"

chatbot_bp = Blueprint("chatbot", __name__)
logger = logging.getLogger("chatbot")
logger.setLevel(logging.DEBUG)

# Handler su stdout
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s"))
    logger.addHandler(ch)


@chatbot_bp.route("/message", methods=["POST"])
def handle_chat_message():
    data = request.get_json(force=True)
    user_input = data.get("message", "").strip()
    thread_id = data.get("thread_id", "default")
    auto_mode = data.get("auto_mode", True)

    if not user_input:
        return jsonify({"response": "⚠️ Inserisci un messaggio valido."}), 400

    # Recupera pipeline con memoria del thread
    try:
        logger.info(f"📥 [{thread_id}] Utente: {user_input}")
        pipeline = get_pipeline_with_memory(thread_id)

        # Stato iniziale (o stato incrementale se già in memoria)
        state = {
            "messages": add_messages([], HumanMessage(content=user_input)),
            "lore": None,
            "domain": None,
            "problem": None,
            "validation": None,
            "error_message": None,
            "last_tool_used": None,
            "history": [],
            "user_preferences": {},
            "auto_mode": auto_mode
        }

        # Esegue il ciclo della pipeline (con memoria persistente)
        config = {"configurable": {"thread_id": thread_id}}
        result = pipeline.invoke(state, config)

        # Costruisce risposta JSON
        resp = {
            "response": result.get("response", "⚠️ Nessuna risposta generata."),
            "domain": result.get("domain"),
            "problem": result.get("problem"),
            "validation": result.get("validation"),
            "last_tool_used": result.get("last_tool_used")
        }

        logger.info(f"✅ [{thread_id}] Bot: {resp['response']!r}")
        return jsonify(resp)

    except Exception as e:
        logger.exception("❌ Errore interno durante l'esecuzione del chatbot.")
        return jsonify({"response": f"❌ Errore interno: {str(e)}"}), 500


@chatbot_bp.route("/reset/<thread_id>", methods=["DELETE"])
def reset_memory(thread_id):
    path = os.path.join("memory", f"{thread_id}.sqlite")
    if os.path.exists(path):
        os.remove(path)
        return jsonify({"status": f"🗑️ Memoria '{thread_id}' cancellata."})
    return jsonify({"status": "⚠️ Nessuna memoria trovata."}), 404
