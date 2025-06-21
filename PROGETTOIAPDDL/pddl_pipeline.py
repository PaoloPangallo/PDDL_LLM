from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict, Optional

from langgraph.checkpoint.sqlite import SqliteSaver

from game.generator import build_prompt_from_lore
from game.utils import ask_ollama, extract_between
from game.validator import validate_pddl
from agent.reflection_agent import refine_pddl  # aggiornato percorso

import logging

logger = logging.getLogger(__name__)


import logging


logger = logging.getLogger(__name__)

# ---------------------
# 1. Stato del flusso
# ---------------------
class PDDLState(TypedDict):
    lore: dict
    prompt: Optional[str]
    domain: Optional[str]
    problem: Optional[str]
    validation: Optional[dict]
    error_message: Optional[str]
    refined_domain: Optional[str]
    refined_problem: Optional[str]

# ---------------------
# 2. Nodi
# ---------------------
def node_build_prompt(state: PDDLState) -> dict:
    prompt, _ = build_prompt_from_lore(state["lore"])
    return {"prompt": prompt}

def node_generate_pddl(state: PDDLState) -> dict:
    response = ask_ollama(state["prompt"])
    domain = extract_between(response, "=== DOMAIN START ===", "=== DOMAIN END ===")
    problem = extract_between(response, "=== PROBLEM START ===", "=== PROBLEM END ===")
    return {"domain": domain, "problem": problem}

def node_validate(state: PDDLState) -> dict:
    domain, problem = state.get("domain"), state.get("problem")
    lore = state.get("lore", {})
    if not domain or not problem:
        return {"validation": None, "error_message": "Missing domain or problem."}
    validation = validate_pddl(domain, problem, lore)
    if not validation.get("valid_syntax", False):
        return {"validation": validation, "error_message": "Invalid PDDL syntax."}
    return {"validation": validation, "error_message": None}

def node_refine(state: PDDLState) -> dict:
    try:
        lore = state.get("lore", {})
        refined = refine_pddl(
            domain_path="TEMP/domain.pddl",  # stub paths if needed
            problem_path="TEMP/problem.pddl",
            error_message=state["error_message"],
            lore=lore
        )
        domain = extract_between(refined, "=== DOMAIN START ===", "=== DOMAIN END ===")
        problem = extract_between(refined, "=== PROBLEM START ===", "=== PROBLEM END ===")
        return {"refined_domain": domain, "refined_problem": problem}
    except Exception as e:
        logger.error("Refine error: %s", e)
        return {"refined_domain": None, "refined_problem": None}

# ---------------------
# 3. Grafo
# ---------------------
workflow = StateGraph(PDDLState)
workflow.add_node("BuildPrompt", node_build_prompt)
workflow.add_node("GeneratePDDL", node_generate_pddl)
workflow.add_node("Validate", node_validate)
workflow.add_node("Refine", node_refine)

workflow.set_entry_point("BuildPrompt")
workflow.add_edge("BuildPrompt", "GeneratePDDL")
workflow.add_edge("GeneratePDDL", "Validate")
workflow.add_conditional_edges(
    "Validate",
    condition=lambda state: "Refine" if state["error_message"] else None,
    path_map={"Refine": "Refine"}
)

checkpointer = SqliteSaver.from_path("checkpoints.sqlite")
# oppure, se usi Postgres:
# checkpointer = PostgresSaver.from_connection_string("postgresql://user:password@host/dbname")


graph = workflow.compile(checkpointer=checkpointer)
