"""Pipeline conversazionale per la generazione, validazione e rifinitura di file PDDL tramite LLM + RAG."""


from typing import Annotated
import json
import os
import logging

from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import tools_condition, ToolNode
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langchain_ollama import ChatOllama
from langchain_core.tools import tool

from game.generator import build_prompt_from_lore, ask_ollama, extract_between
from game.validator import validate_pddl
from agent.reflection_agent import refine_pddl
from game.utils import save_text_file
from db.db import retrieve_similar_examples_from_db

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ================================
# 1. Stato condiviso
# ================================
class ChatState(TypedDict):
    """
    Stato condiviso della pipeline conversazionale:
    - messages: cronologia della chat
    - lore: JSON in formato stringa
    - domain / problem: file PDDL
    - validation: risultato della validazione
    - error_message: eventuale errore da validazione
    """
    messages: Annotated[list[BaseMessage], add_messages]
    lore: str | None
    domain: str | None
    problem: str | None
    validation: str | None
    error_message: str | None


# ================================
# 2. Tools LangChain
# ================================
@tool
def generate_pddl_from_lore(lore: str) -> dict:
    """
    Genera i file PDDL (domain e problem) da un lore in formato JSON.
    Include esempi rilevanti (RAG) dal database locale.
    """
    lore_dict = json.loads(lore)
    examples = retrieve_similar_examples_from_db(lore_dict, k=0)
    prompt, _ = build_prompt_from_lore(lore_dict, examples=examples)
    result = ask_ollama(prompt)

    domain = extract_between(result, "=== DOMAIN START ===", "=== DOMAIN END ===")
    problem = extract_between(result, "=== PROBLEM START ===", "=== PROBLEM END ===")

    return {"domain": domain, "problem": problem, "lore": lore}


@tool
def validate(domain: str, problem: str, lore: str) -> dict:
    """
    Valida i file PDDL generati usando il lore.
    """
    validation = validate_pddl(domain, problem, json.loads(lore))
    return {
        "validation": str(validation),
        "error_message": None if validation.get("valid_syntax") else "Invalid syntax"
    }


@tool
def reflect(domain: str, problem: str, error_message: str, lore: str) -> dict:
    """
    Raffina i file PDDL sulla base dell'errore segnalato e del lore.
    """
    os.makedirs("TEMP", exist_ok=True)
    save_text_file("TEMP/domain.pddl", domain)
    save_text_file("TEMP/problem.pddl", problem)

    refined = refine_pddl(
        domain_path="TEMP/domain.pddl",
        problem_path="TEMP/problem.pddl",
        error_message=error_message,
        lore=json.loads(lore)
    )

    domain = extract_between(refined, "=== DOMAIN START ===", "=== DOMAIN END ===")
    problem = extract_between(refined, "=== PROBLEM START ===", "=== PROBLEM END ===")
    return {"domain": domain, "problem": problem}


# ================================
# 3. Setup LLM con Tools
# ================================
tools = [generate_pddl_from_lore, validate, reflect]
llm = ChatOllama(model="llama3.2-vision")
llm_with_tools = llm.bind_tools(tools)


# ================================
# 4. Costruzione del grafo
# ================================
def chat_node(state: ChatState) -> dict:
    """Nodo conversazionale: invoca LLM con gli strumenti."""
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": state["messages"] + [response]}


builder = StateGraph(ChatState)
builder.add_node("chat", chat_node)
builder.add_node("tools", ToolNode(tools=tools))
builder.add_conditional_edges("chat", path=tools_condition)
builder.add_edge("tools", "chat")
builder.add_edge(START, "chat")

graph = builder.compile()


# ================================
# 5. Gestione memoria persistente
# ================================
def get_memory_for_thread(thread_id: str) -> SqliteSaver:
    """Recupera o crea la memoria persistente per un thread."""
    memory_dir = "memory"
    os.makedirs(memory_dir, exist_ok=True)
    return SqliteSaver.from_path(os.path.join(memory_dir, f"{thread_id}.sqlite"))


# ================================
# 6. Loop REPL o API
# ================================
def process_input(user_input: str, thread_id: str):
    """Processa input utente tramite grafo con memoria per thread."""
    if user_input.strip().lower() == "/reset":
        path = os.path.join("memory", f"{thread_id}.sqlite")
        if os.path.exists(path):
            os.remove(path)
            print("🔄 Memoria del thread resettata.")
        else:
            print("ℹ️ Nessuna memoria da resettare.")
        return

    state = {"messages": [{"role": "user", "content": user_input}]}
    config = {"configurable": {"thread_id": thread_id}}

    memory = get_memory_for_thread(thread_id)
    graph_with_memory = graph.with_config(checkpointer=memory)

    for update in graph_with_memory.stream(state, config, stream_mode="values"):
        response_msg = update["messages"][-1]
        print(f"🤖: {response_msg.content}")


# ================================
# 7. Esecuzione CLI
# ================================
if __name__ == "__main__":
    print("== QuestMaster ChatBot 🧠 ==")
    thread = input("🧵 Thread ID: ")
    while True:
        user_msg = input("👤 Tu: ")
        if user_msg.lower() in {"q", "quit", "exit"}:
            break
        process_input(user_msg, thread)
