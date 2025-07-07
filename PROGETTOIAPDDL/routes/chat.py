# routes/chat.py

from flask import Blueprint, request, jsonify

chat_bp = Blueprint("chat", __name__)

@chat_bp.route("/api/chat", methods=["POST"])
def chat_api():
    data = request.get_json(force=True)
    
    user_message = data.get("message", "")
    thread_id = data.get("thread_id", "default")

    if not user_message.strip():
        return jsonify({"error": "Messaggio utente mancante."}), 400

    try:
        state = {"messages": [{"role": "user", "content": user_message}]}
        config = {"configurable": {"thread_id": thread_id}}

        last_response = ""
        

        return jsonify({"reply": last_response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
