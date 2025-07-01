# routes/chat_bot.py

from flask import Blueprint, request, jsonify
import uuid
from typing import List, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_tavily import TavilySearch

chatbot_bp = Blueprint("chatbot", __name__)

class ChatState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

# Costruzione grafo, modello, tool (come da esempio)

graph_builder = StateGraph(ChatState)
llm = ChatOllama(model="mistral")
search_tool = TavilySearch(max_results=2)
llm_with_tools = llm.bind_tools([search_tool])

def chatbot_node(state: ChatState):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

graph_builder.add_node("chatbot", chatbot_node)
graph_builder.add_node("tools", ToolNode(tools=[search_tool]))
graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")

checkpointer = MemorySaver()
graph = graph_builder.compile(checkpointer=checkpointer)

# Route API

@chatbot_bp.route("/message", methods=["POST"])
def message():
    data = request.json or {}
    thread_id = data.get("thread_id") or str(uuid.uuid4())
    checkpoint_id = data.get("checkpoint_id")
    user_message = data.get("message")

    if not user_message:
        return jsonify({"error": "Missing 'message'"}), 400

    init_state = {"messages": [{"role": "user", "content": user_message}]}
    cfg = {"configurable": {"thread_id": thread_id}}
    if checkpoint_id:
        cfg["configurable"]["checkpoint_id"] = checkpoint_id

    responses = []
    for ev in graph.stream(init_state, cfg, stream_mode="values"):
        if "messages" in ev:
            responses.append(ev["messages"][-1].content)

    return jsonify({
        "thread_id": thread_id,
        "checkpoint_id": cfg["configurable"].get("checkpoint_id"),
        "responses": responses
    })

@chatbot_bp.route("/history", methods=["GET"])
def history():
    thread_id = request.args.get("thread_id")
    if not thread_id:
        return jsonify({"error": "Missing thread_id"}), 400

    cfg = {"configurable": {"thread_id": thread_id}}
    history = graph.get_state_history(cfg)
    data = []
    for idx, snap in enumerate(history):
        n_msgs = len(snap.values["messages"])
        next_node = snap.next or "END"
        ts = snap.config["configurable"].get("checkpoint_id", "-")
        data.append({
            "index": idx,
            "messages_count": n_msgs,
            "next_node": next_node,
            "checkpoint_id": ts,
        })
    return jsonify(data)

@chatbot_bp.route("/replay", methods=["POST"])
def replay():
    data = request.json or {}
    thread_id = data.get("thread_id")
    checkpoint_id = data.get("checkpoint_id")

    if not thread_id or not checkpoint_id:
        return jsonify({"error": "Missing thread_id or checkpoint_id"}), 400

    cfg = {"configurable": {"thread_id": thread_id, "checkpoint_id": checkpoint_id}}

    responses = []
    for event in graph.stream(None, cfg, stream_mode="values"):
        if "messages" in event:
            responses.append(event["messages"][-1].content)

    return jsonify({"responses": responses})
