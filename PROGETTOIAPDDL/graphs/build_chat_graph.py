"""Costruzione del grafo conversazionale con LLM + tool PDDL (generate, validate, reflect)."""

import os
import json
from typing import Annotated, Optional, List
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import tools_condition, ToolNode

from langchain_core.messages import BaseMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama

from core.generator import build_prompt_from_lore, ask_ollama, extract_between
from core.validator import validate_pddl
from agents.reflection_agent import refine_pddl
from core.utils import save_text_file
from db.db import retrieve_similar_examples_from_db

# ================================
# 1. Stato condiviso
# ================================
class ChatState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    lore: Optional[str]
    domain: Optional[str]
    problem: Optional[str]
    validation: Optional[str]
    error_message: Optional[str]

# ================================
# 2. Tools LangChain
# ================================
@tool
def generate_pddl_from_lore(lore: str) -> dict:
    """
    Genera i file PDDL (domain e problem) a partire da un lore in formato JSON.
    Utilizza esempi rilevanti (RAG) e un modello LLM per costruire il prompt.
    """
    lore_dict = json.loads(lore)
    examples = retrieve_similar_examples_from_db(lore_dict, k=1)
    prompt, _ = build_prompt_from_lore(lore_dict, examples=examples)
    result = ask_ollama(prompt)
    domain = extract_between(result, "=== DOMAIN START ===", "=== DOMAIN END ===")
    problem = extract_between(result, "=== PROBLEM START ===", "=== PROBLEM END ===")
    return {"domain": domain, "problem": problem, "lore": lore}


@tool
def validate(domain: str, problem: str, lore: str) -> dict:
    """
    Valida i file PDDL (domain e problem) generati, confrontandoli con il contenuto del lore.
    Restituisce il risultato della validazione e un eventuale messaggio d'errore.
    """
    validation = validate_pddl(domain, problem, json.loads(lore))
    return {
        "validation": str(validation),
        "error_message": None if validation.get("valid_syntax") else "Invalid syntax"
    }


@tool
def reflect(domain: str, problem: str, error_message: str, lore: str) -> dict:
    """
    Raffina i file PDDL a partire dagli errori di validazione e dal contenuto del lore.
    Usa un LLM per correggere e rigenerare domain e problem coerenti.
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
# 3. Costruzione del grafo
# ================================
def build_chat_graph():
    """Costruisce il grafo conversazionale con i tool PDDL e un LLM abilitato all'invocazione strumenti."""
    tools = [generate_pddl_from_lore, validate, reflect]
    llm = ChatOllama(model="mistral")
    llm_with_tools = llm.bind_tools(tools)

    def chat_node(state: ChatState) -> dict:
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": state["messages"] + [response]}

    builder = StateGraph(ChatState)
    builder.add_node("chat", chat_node)
    builder.add_node("tools", ToolNode(tools=tools))
    builder.add_conditional_edges("chat", path=tools_condition)
    builder.add_edge("tools", "chat")
    builder.add_edge(START, "chat")

    return builder.compile(checkpointer=MemorySaver())
