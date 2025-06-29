from typing import Annotated
import json
import os

from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import tools_condition, ToolNode
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langchain_ollama import ChatOllama
from langchain_core.tools import tool

from game.generator import build_prompt_from_lore, ask_ollama, extract_between
from game.validator import validate_pddl
from agent.reflection_agent import refine_pddl


# 1. Stato della conversazione
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    lore: str | None
    domain: str | None
    problem: str | None
    validation: str | None
    error_message: str | None


# 2. Tools LangChain che usano i tuoi moduli reali
@tool
def generate_pddl_from_lore(lore: str) -> dict:
    """
    Generate domain and problem PDDL files from a given lore in JSON format.
    """
    prompt, _ = build_prompt_from_lore(json.loads(lore))
    result = ask_ollama(prompt)
    domain = extract_between(result, "=== DOMAIN START ===", "=== DOMAIN END ===")
    problem = extract_between(result, "=== PROBLEM START ===", "=== PROBLEM END ===")
    return {"domain": domain, "problem": problem, "lore": lore}


@tool
def validate(domain: str, problem: str, lore: str) -> dict:
    """
    Validate the given domain and problem PDDL files using the provided lore.
    """
    validation = validate_pddl(domain, problem, json.loads(lore))
    return {
        "validation": str(validation),
        "error_message": None if validation.get("valid_syntax") else "Invalid syntax"
    }


@tool
def reflect(domain: str, problem: str, error_message: str, lore: str) -> dict:
    """
    Refine the PDDL files based on the validation error and the given lore.
    """
    refined = refine_pddl(
        domain_path="TEMP/domain.pddl",
        problem_path="TEMP/problem.pddl",
        error_message=error_message,
        lore=json.loads(lore)
    )
    domain = extract_between(refined, "=== DOMAIN START ===", "=== DOMAIN END ===")
    problem = extract_between(refined, "=== PROBLEM START ===", "=== PROBLEM END ===")
    return {"domain": domain, "problem": problem}


# 3. Setup LLM e tools
tools = [generate_pddl_from_lore, validate, reflect]
llm = ChatOllama(model="mistral")
llm_with_tools = llm.bind_tools(tools)


# 4. Grafo conversazionale
builder = StateGraph(ChatState)
builder.add_node("chat", lambda state: {"messages": [llm_with_tools.invoke(state["messages"])]})
builder.add_node("tools", ToolNode(tools=tools))
builder.add_conditional_edges("chat", path=tools_condition)
builder.add_edge("tools", "chat")
builder.add_edge(START, "chat")
graph = builder.compile()


# 5. Funzione per caricare memoria da file per thread
def get_memory_for_thread(thread_id: str) -> MemorySaver:
    memory_dir = "memory"
    os.makedirs(memory_dir, exist_ok=True)
    return MemorySaver.from_path(os.path.join(memory_dir, f"{thread_id}.json"))  # type: ignore[attr-defined]



# 6. Funzione REPL o API
def process_input(user_input: str, thread_id: str):
    # Comando speciale per resettare la memoria
    if user_input.strip().lower() == "/reset":
        path = os.path.join("memory", f"{thread_id}.json")
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


# 7. Esecuzione CLI
if __name__ == "__main__":
    print("== QuestMaster ChatBot ==")
    thread = input("Thread ID: ")
    while True:
        user_msg = input("Tu: ")
        if user_msg.lower() in {"q", "quit", "exit"}:
            break
        process_input(user_msg, thread)
