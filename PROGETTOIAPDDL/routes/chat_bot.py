from flask import Blueprint, request, jsonify
from graphs.build_chat_graph import build_chat_graph
from langgraph.checkpoint.sqlite import SqliteSaver
import os

chatbot_bp = Blueprint("chatbot", __name__)
graph = build_chat_graph()

def get_memory_for_thread(thread_id: str) -> SqliteSaver:
    memory_dir = "memory"
    os.makedirs(memory_dir, exist_ok=True)
    return SqliteSaver.from_path(os.path.join(memory_dir, f"{thread_id}.sqlite"))

@chatbot_bp.route("/message", methods=["POST"])
def handle_chat_message():
    data = request.get_json()
    user_input = data.get("message", "")
    thread_id = data.get("thread_id", "default")

    state = {"messages": [{"role": "user", "content": user_input}]}
    config = {"configurable": {"thread_id": thread_id}}

    memory = get_memory_for_thread(thread_id)
    graph_with_memory = graph.with_config(checkpointer=memory)

    for update in graph_with_memory.stream(state, config, stream_mode="values"):
        response_msg = update["messages"][-1]
        return jsonify({"response": response_msg.content})
