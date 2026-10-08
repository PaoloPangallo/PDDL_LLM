import os
import json
import logging
import shutil
from flask import Blueprint, request, jsonify, url_for, Response, stream_with_context
from langchain_core.messages import HumanMessage, BaseMessage
from graphs.pddl_pipeline_graph import get_pipeline_with_memory
from core.safe_paths import validate_thread_id, resolve_lore_file
from pathlib import Path

LORE_DIRECTORY = Path(__file__).resolve().parents[1] / "lore"

pipeline_chat_bp = Blueprint("pipeline_chat", __name__)
logger = logging.getLogger("pipeline_chat")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    
    
def serialize_value(val):
    if isinstance(val, BaseMessage):
        return {"type": val.type, "content": val.content}
    elif isinstance(val, list):
        return [serialize_value(v) for v in val]
    elif isinstance(val, dict):
        return {k: serialize_value(v) for k, v in val.items()}
    return val



@pipeline_chat_bp.route("/message", methods=["POST"])
def handle_pipeline_chat():
    """
    Endpoint classico: esegue tutta la pipeline e restituisce JSON
    con prompt, risposta, validazione, file generati e URL di download.
    """
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Expected JSON object"}), 400
        logger.debug("📥 Dati ricevuti: %r", list(data))

        try:
            thread_id = validate_thread_id(data.get("thread_id", "session-1"))
            lore_path = resolve_lore_file(data.get("lore"), LORE_DIRECTORY)
        except (ValueError, FileNotFoundError) as exc:
            return jsonify({"error": str(exc)}), 400
        user_message = data.get("message", "")
        if not isinstance(user_message, str):
            return jsonify({"error": "message must be text"}), 400
        user_message = user_message.strip()
        reset = data.get("reset", False)

        with lore_path.open(encoding="utf-8") as lore_file:
            lore = json.load(lore_file)

        # ✅ Reset memoria se richiesto
        memory_path = os.path.join("memory", f"{thread_id}.sqlite")
        if reset and os.path.exists(memory_path):
            os.remove(memory_path)
            logger.warning("🧹 Memoria cancellata per nuova run: %s", memory_path)

        # Ottieni pipeline persistente
        graph = get_pipeline_with_memory(thread_id, reset=reset)


        # Recupera stato se esiste
        try:
            snapshot = graph.get_state(config={"configurable": {"thread_id": thread_id}})
            state = dict(getattr(snapshot, "values", None) or {})
            logger.info("♻️ Stato recuperato da checkpoint")
        except Exception:
            state = {}
            logger.info("🆕 Nessun checkpoint precedente, nuova run")

        state["lore"] = lore
        state["thread_id"] = thread_id
        state.setdefault("messages", [])
        state.setdefault("status", "ok")
        state.setdefault("refine_attempts", 0)

        # Invoca la pipeline con o senza feedback umano
        if user_message:
            logger.info("✍️ Feedback umano: invio messaggio a ChatFeedback")
            state["messages"].append(HumanMessage(content=user_message))
            result = graph.invoke(state, config={"configurable": {"thread_id": thread_id}})


        else:
            logger.info("⚡ Avvio pipeline completa")
            result = graph.invoke(state)

        # Estrai risposta AI (se presente)
        response_text = None
        for msg in result.get("messages", []):
            if isinstance(msg, BaseMessage) and msg.type == "ai":
                response_text = msg.content
            elif isinstance(msg, dict) and msg.get("type") == "ai":
                response_text = msg.get("content")

        # Salva file in static/generated/<thread_id>/
        gen_dir = os.path.join("static", "generated", thread_id)
        os.makedirs(gen_dir, exist_ok=True)

        files_map = {
            "raw_response":   "raw_response.txt",
            "domain":         "domain.pddl",
            "problem":        "problem.pddl",
            "refined_domain": "domain_refined.pddl",
            "refined_problem":"problem_refined.pddl",
        }
        urls = {}
        tmp = result.get("tmp_dir")
        if tmp:
            for field, fname in files_map.items():
                src = os.path.join(tmp, fname)
                if os.path.exists(src):
                    dst = os.path.join(gen_dir, fname)
                    shutil.copy(src, dst)
                    urls[f"{field}_url"] = url_for(
                        "static", filename=f"generated/{thread_id}/{fname}"
                    )

        # Prepara risposta JSON
        payload = {
            "response":        response_text or "⚠️ Nessuna risposta generata.",
            "prompt":          result.get("prompt"),
            "validation":      result.get("validation"),
            "refined_domain":  result.get("refined_domain"),
            "refined_problem": result.get("refined_problem"),
            **urls
        }
        return jsonify(payload)

    except Exception as e:
        logger.exception("❌ Errore durante l'esecuzione della pipeline")
        return jsonify({"error": str(e)}), 500


@pipeline_chat_bp.route("/stream", methods=["GET"])
def stream_pipeline():
    try:
        thread_id = validate_thread_id(request.args.get("thread_id", "session-1"))
        lore_path = resolve_lore_file(request.args.get("lore"), LORE_DIRECTORY)
    except (ValueError, FileNotFoundError) as exc:
        return str(exc), 400

    with lore_path.open(encoding="utf-8") as f:
        lore = json.load(f)

    reset = request.args.get("reset", "false").lower() == "true"
    graph = get_pipeline_with_memory(thread_id, reset=reset)

    state = {"lore": lore, "thread_id": thread_id,
             "messages": [], "status": "ok", "attempt": 0}

    def event_stream():
        # ognuno di questi chunk è un dict con i campi modificati
        for chunk in graph.stream(state):
            # per ogni chiave nel chunk emettiamo un evento SSE con nome = chiave
            for key, val in chunk.items():
                # converto in json la porzione di stato
                data = json.dumps(serialize_value(val), ensure_ascii=False)

                yield f"event: {key}\ndata: {data}\n\n"

        # segnale di fine
        yield "event: done\ndata: {}\n\n"

    return Response(stream_with_context(event_stream()),
                    mimetype="text/event-stream")
    
    
    
