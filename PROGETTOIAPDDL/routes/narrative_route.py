import os
import json
import logging
from flask import Blueprint, render_template, request, jsonify, Response, stream_with_context

from graphs.narrative_graph import get_pipeline_with_memory

narrative_bp = Blueprint("narrative", __name__, url_prefix="/narrative")
logger = logging.getLogger("narrative_route")


@narrative_bp.route("/", methods=["GET"])
def narrative_page():
    lore_files = os.listdir("lore")
    return render_template("narrative.html", lore_files=lore_files)


@narrative_bp.route("/start", methods=["POST"])
def start_narrative():
    try:
        data = request.get_json() or {}
        thread_id = data.get("thread_id", "session-1")
        lore_name = data.get("lore")
        logger.info(f"🚀 Inizio narrazione: {thread_id}")

        if not lore_name:
            return jsonify({"error": "lore mancante"}), 400

        lore_path = os.path.join("lore", lore_name)
        if not os.path.exists(lore_path):
            return jsonify({"error": f"Il file lore '{lore_name}' non esiste."}), 400

        with open(lore_path, encoding="utf-8") as f:
            lore = json.load(f)

        graph = get_pipeline_with_memory(thread_id)
        state = {
            "thread_id": thread_id,
            "lore": lore,
            "current_step": 0,
            "plan_steps": [],
        }
        result = graph.invoke(state)

        step = result.get("latest_step")
        return jsonify({"thread_id": thread_id, "step": step, "done": False}), 200

    except Exception as e:
        logger.exception("❌ Errore in /narrative/start")
        return jsonify({"error": str(e)}), 500


@narrative_bp.route("/message", methods=["POST"])
def narrative_message():
    try:
        data = request.get_json() or {}
        thread_id = data.get("thread_id")
        feedback = data.get("feedback", "").strip()

        if not thread_id:
            return jsonify({"error": "thread_id mancante"}), 400

        logger.info(f"📨 Step successivo per thread: {thread_id}")
        graph = get_pipeline_with_memory(thread_id)
        state = {"thread_id": thread_id}
        if feedback:
            state["chat_feedback"] = feedback
            logger.debug(f"✍️ Feedback utente: {feedback}")

        result = graph.invoke(state)
        is_done = result.get("current_step", 0) >= len(result.get("plan_steps", []))

        return jsonify({
            "thread_id": thread_id,
            "step": result.get("latest_step") if not is_done else None,
            "done": is_done
        }), 200

    except Exception as e:
        logger.exception("❌ Errore in /narrative/message")
        return jsonify({"error": str(e)}), 500


@narrative_bp.route("/stream")
def narrative_stream():
    """
    Server-Sent Events endpoint for interactive narrative.
    Query params: thread_id, lore, (optional) feedback
    """
    thread_id = request.args.get("thread_id")
    lore_name = request.args.get("lore")
    feedback = request.args.get("feedback")

    if not thread_id or not lore_name:
        return "thread_id o lore mancanti", 400

    lore_path = os.path.join("lore", lore_name)
    if not os.path.exists(lore_path):
        return f"lore {lore_name} non trovata", 404

    with open(lore_path, encoding="utf-8") as f:
        lore = json.load(f)

    graph = get_pipeline_with_memory(thread_id, reset=False)
    state = {
        "thread_id": thread_id,
        "lore": lore,
        "current_step": 0,
        "plan_steps": []
    }
    if feedback:
        state["chat_feedback"] = feedback

    def event_stream():
        for chunk in graph.stream(state):
            for event_name, payload in chunk.items():
                data = json.dumps(payload, ensure_ascii=False)
                yield f"event: {event_name}\ndata: {data}\n\n"
        yield "event: done\ndata: {}\n\n"

    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")
