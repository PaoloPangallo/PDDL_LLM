import os
import json
import logging
from flask import Blueprint, render_template, request, jsonify, Response, stream_with_context

from graphs.narrative_graph import get_pipeline_with_memory

narrative_bp = Blueprint("narrative", __name__, url_prefix="/narrative")
logger = logging.getLogger("narrative_route")


# === Pagina HTML principale ===
@narrative_bp.route("/", methods=["GET"])
def narrative_page():
    lore_files = os.listdir("lore")
    return render_template("narrative.html", lore_files=lore_files)


# === Avvio narrazione ===
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

        graph = get_pipeline_with_memory(thread_id, reset=False)

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


# === Inoltro feedback utente ===
@narrative_bp.route("/message", methods=["POST"])
def narrative_message():
    try:
        data = request.get_json() or {}
        thread_id = data.get("thread_id")
        feedback = data.get("feedback", "").strip()

        if not thread_id:
            return jsonify({"error": "thread_id mancante"}), 400
        if not feedback:
            return jsonify({"error": "feedback mancante"}), 400

        logger.info(f"📨 Feedback ricevuto per thread: {thread_id} → {feedback}")
        graph = get_pipeline_with_memory(thread_id, reset=False)

        result = graph.send_input("chat_feedback", feedback)

        is_done = result.get("current_step", 0) >= len(result.get("plan_steps", []))

        return jsonify({
            "thread_id": thread_id,
            "step": result.get("latest_step") if not is_done else None,
            "done": is_done
        }), 200

    except Exception as e:
        logger.exception("❌ Errore in /narrative/message")
        return jsonify({"error": str(e)}), 500


# === Streaming interattivo ===
@narrative_bp.route("/stream")
def narrative_stream():
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
        logger.info(f"🔁 Avvio stream narrativo per thread: {thread_id}")

        for chunk in graph.stream(state):
            logger.debug("📦 Chunk ricevuto: %s", chunk)

            for event_name, payload in chunk.items():

                # 🛑 Gestione interrupt → ChatFeedback
                if event_name == "__interrupt__" and isinstance(payload, tuple):
                    interrupt_obj = payload[0]
                    event_name = "ChatFeedback"  # 🚨 Case-sensitive!
                    payload = {
                        "message": interrupt_obj.value,
                        "resumable": interrupt_obj.resumable,
                        "namespace": getattr(interrupt_obj, "ns", [])
                    }

                # ✅ Serializzazione JSON sicura
                try:
                    data = json.dumps(payload, ensure_ascii=False)
                except Exception as e:
                    logger.warning(f"⚠️ Errore serializzazione JSON per evento '{event_name}': {e}")
                    data = json.dumps({"error": str(e)})

                logger.info(f"➡️ Evento emesso: {event_name} ({len(data)} bytes)")
                if event_name == "PlanLoaded":
                    logger.debug("🗺️ Dati del piano: %s", data[:500])

                yield f"event: {event_name}\ndata: {data}\n\n"

        yield "event: Done\ndata: {}\n\n"
        logger.info("✅ Fine stream narrativa.")

    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")
