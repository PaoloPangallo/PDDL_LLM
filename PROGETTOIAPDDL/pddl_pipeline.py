"""
Pipeline LangGraph per generare, validare e raffinare file PDDL a partire da una lore.
Include RAG (Retrieval-Augmented Generation) da database locale.
"""

import os
import json
import logging
import tempfile
from typing import TypedDict, Optional, Union

from langgraph.graph import StateGraph

from core.generator import build_prompt_from_lore
from db.db import retrieve_similar_examples_from_db
from core.utils import ask_ollama, extract_between, save_text_file
from core.validator import validate_pddl
from agents.reflection_agent import refine_pddl

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


# ---------------------
# Stati tipizzati
# ---------------------
class InputState(TypedDict):
    lore: dict
    tmp_dir: str
    prompt: Optional[str]
    status: str  # "ok" o "failed"

class OutputState(TypedDict, total=False):
    domain: str
    problem: str
    validation: dict
    error_message: str
    refined_domain: str
    refined_problem: str

PDDLState = InputState.__annotations__  # union di tutti i campi


# ---------------------
# Nodi pipeline
# ---------------------
def node_build_prompt(state: InputState) -> dict:
    """Costruisce tmp_dir e prompt da lore + RAG."""
    # 1) Crea una cartella temporanea univoca
    tmp_dir = tempfile.mkdtemp(prefix="pddl_")
    logger.debug("🧠 [BuildPrompt] tmp_dir creato: %s", tmp_dir)

    # 2) Recupera esempi simili
    examples_raw = retrieve_similar_examples_from_db(state["lore"], k=1)
    examples = [e for e in examples_raw if isinstance(e, str)]
    prompt, _ = build_prompt_from_lore(state["lore"], examples=examples)

    logger.debug("📚 [BuildPrompt] Prompt (prime 300 char): %s", prompt[:300])

    return {
        "tmp_dir": tmp_dir,
        "prompt": prompt,
        "status": "ok"
    }


def node_generate_pddl(state: InputState) -> dict:
    """Invia prompt a LLM, salva domain/problem in tmp_dir."""
    if state.get("status") != "ok":
        return {"status": "failed", "error_message": "Skipped generate (bad status)"}

    tmp = state["tmp_dir"]
    try:
        response = ask_ollama(state["prompt"])
        domain = extract_between(response, "=== DOMAIN START ===", "=== DOMAIN END ===")
        problem = extract_between(response, "=== PROBLEM START ===", "=== PROBLEM END ===")

        if not domain or not problem:
            raise ValueError("Estrazione dominio o problema fallita")

        save_text_file(os.path.join(tmp, "domain.pddl"), domain)
        save_text_file(os.path.join(tmp, "problem.pddl"), problem)

        return {"domain": domain, "problem": problem, "status": "ok"}
    except Exception as e:
        logger.error("❌ [GeneratePDDL] %s", e, exc_info=True)
        return {"domain": "", "problem": "", "status": "failed", "error_message": str(e)}


def node_validate(state: InputState) -> dict:
    """Valida domain/problem salvati e setta error_message o validation."""
    if state.get("status") != "ok":
        return {"status": "failed", "error_message": "Skipped validate"}

    domain = state.get("domain", "")
    problem = state.get("problem", "")
    lore = state["lore"]

    if not domain or not problem:
        msg = "Domain o problem mancanti"
        return {"status": "failed", "error_message": msg}

    try:
        validation = validate_pddl(domain, problem, lore)
        valid_syntax = validation.get("valid_syntax", False)
        sem_err = validation.get("semantic_errors", [])
        status = "ok" if valid_syntax and not sem_err else "failed"
        err_msg = None if status == "ok" else "Validation errors"

        logger.debug("📋 [Validate] %s", json.dumps(validation, indent=2))
        return {"validation": validation, "status": status, "error_message": err_msg}
    except Exception as e:
        logger.error("❌ [Validate] %s", e, exc_info=True)
        return {"status": "failed", "error_message": str(e)}


def node_refine(state: InputState) -> dict:
    """Raffina se validation è fallita."""
    if state.get("status") != "failed":
        return {"status": "ok"}  # skip refine

    tmp = state["tmp_dir"]
    err = state.get("error_message", "error")
    lore = state["lore"]

    try:
        updated = refine_pddl(
            domain_path=os.path.join(tmp, "domain.pddl"),
            problem_path=os.path.join(tmp, "problem.pddl"),
            error_message=err,
            lore=lore
        )
        rd = extract_between(updated, "=== DOMAIN START ===", "=== DOMAIN END ===")
        rp = extract_between(updated, "=== PROBLEM START ===", "=== PROBLEM END ===")

        save_text_file(os.path.join(tmp, "domain_refined.pddl"), rd)
        save_text_file(os.path.join(tmp, "problem_refined.pddl"), rp)

        return {
            "refined_domain": rd,
            "refined_problem": rp,
            "status": "ok"
        }
    except Exception as e:
        logger.error("❌ [Refine] %s", e, exc_info=True)
        return {"status": "failed", "error_message": str(e)}


def end_node(state: InputState) -> dict:
    """Restituisce solo i campi di output utili."""
    logger.debug("✅ [End] state finale: %s", state)
    out: OutputState = {}
    for key in ("domain", "problem", "validation", "error_message", "refined_domain", "refined_problem"):
        if key in state:
            out[key] = state[key]
    return out


# ---------------------
# Branching
# ---------------------
def should_refine(state: InputState) -> str:
    # Se status ancora "ok" e valid_syntax ok => End, altrimenti Refine
    if state.get("status") == "ok" and state.get("validation", {}).get("valid_syntax", False):
        return "End"
    return "Refine"


# ---------------------
# Costruzione grafo
# ---------------------
builder = StateGraph(InputState, stateful=False)
builder.add_node("BuildPrompt", node_build_prompt)
builder.add_node("GeneratePDDL", node_generate_pddl)
builder.add_node("Validate", node_validate)
builder.add_node("Refine", node_refine)
builder.add_node("End", end_node)

builder.set_entry_point("BuildPrompt")
builder.add_edge("BuildPrompt", "GeneratePDDL")
builder.add_edge("GeneratePDDL", "Validate")
builder.add_conditional_edges("Validate", path=should_refine)

pipeline = builder.compile()


# ---------------------
# Test locale
# ---------------------
if __name__ == "__main__":
    with open("lore/example_lore.json", encoding="utf-8") as f:
        lore_data = json.load(f)
    result = pipeline.invoke({"lore": lore_data})
    print("=== Risultato finale ===\n", json.dumps(result, indent=2, ensure_ascii=False))
