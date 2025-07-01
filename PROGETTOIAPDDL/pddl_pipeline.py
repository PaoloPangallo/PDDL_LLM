"""
Pipeline LangGraph per generare, validare e raffinare file PDDL a partire da una lore.
Include RAG (Retrieval-Augmented Generation) da database locale.
"""

import os
import json
import logging
from typing import TypedDict, Optional

from langgraph.graph import StateGraph
from game.generator import build_prompt_from_lore
from game.utils import ask_ollama, extract_between, save_text_file
from game.validator import validate_pddl
from agent.reflection_agent import refine_pddl
from db.db import retrieve_similar_examples_from_db

# ---------------------
# Logging setup
# ---------------------
logger = logging.getLogger("pddl_pipeline")
logging.basicConfig(level=logging.INFO)

# ---------------------
# Stato del flusso
# ---------------------
class PDDLState(TypedDict, total=False):
    """Stato condiviso tra i nodi della pipeline PDDL."""
    lore: dict
    prompt: Optional[str]
    domain: Optional[str]
    problem: Optional[str]
    validation: Optional[dict]
    error_message: Optional[str]
    refined_domain: Optional[str]
    refined_problem: Optional[str]
    refine_count: int

IS_LOCAL_RUN = __name__ == "__main__"
MAX_REFINES = 2

# ---------------------
# Nodi della pipeline
# ---------------------
def node_build_prompt(state: PDDLState) -> dict:
    logger.info("🧠 [BuildPrompt] Costruzione del prompt in corso...")
    examples_raw = retrieve_similar_examples_from_db(state["lore"], k=1)
    examples = [e for e in examples_raw if isinstance(e, str)]
    prompt, _ = build_prompt_from_lore(state["lore"], examples=examples)

    logger.info("📚 [BuildPrompt] %d esempio/i recuperati dal DB.", len(examples))
    logger.debug("📝 Prompt:\n%s", prompt[:300])
    return {"prompt": prompt}


def node_generate_pddl(state: PDDLState) -> dict:
    logger.info("🤖 [GeneratePDDL] Invio prompt al modello...")
    try:
        response = ask_ollama(state["prompt"])
        domain = extract_between(response, "=== DOMAIN START ===", "=== DOMAIN END ===")
        problem = extract_between(response, "=== PROBLEM START ===", "=== PROBLEM END ===")

        if not domain or not problem:
            raise ValueError("Estrazione dominio o problema fallita")

        if IS_LOCAL_RUN:
            os.makedirs("TEMP", exist_ok=True)
            save_text_file("TEMP/domain.pddl", domain)
            save_text_file("TEMP/problem.pddl", problem)

        logger.info("✅ [GeneratePDDL] File generati correttamente.")
        return {"domain": domain, "problem": problem}
    except Exception as err:
        logger.error("❌ Errore nella generazione: %s", err, exc_info=True)
        return {"domain": None, "problem": None, "error_message": str(err)}


def node_validate(state: PDDLState) -> dict:
    logger.info("🧪 [Validate] Validazione in corso...")
    domain, problem, lore = state.get("domain"), state.get("problem"), state.get("lore", {})

    if not domain or not problem:
        return {"validation": None, "error_message": "Missing domain or problem for validation."}

    try:
        validation = validate_pddl(domain, problem, lore)
        logger.info("📋 [Validate] valid_syntax = %s", validation.get("valid_syntax"))
        return {
            "validation": validation,
            "error_message": None if validation.get("valid_syntax") else "Invalid PDDL syntax."
        }
    except Exception as err:
        logger.error("❌ Errore durante la validazione: %s", err, exc_info=True)
        return {"validation": None, "error_message": f"Errore nella validazione: {str(err)}"}


def node_refine(state: PDDLState) -> dict:
    logger.info("🔁 [Refine] Raffinamento in corso...")
    try:
        if IS_LOCAL_RUN:
            os.makedirs("TEMP", exist_ok=True)
            save_text_file("TEMP/domain.pddl", state["domain"])
            save_text_file("TEMP/problem.pddl", state["problem"])

        refined = refine_pddl(
            domain_path="TEMP/domain.pddl",
            problem_path="TEMP/problem.pddl",
            error_message=state["error_message"],
            lore=state.get("lore", {})
        )

        domain = extract_between(refined, "=== DOMAIN START ===", "=== DOMAIN END ===")
        problem = extract_between(refined, "=== PROBLEM START ===", "=== PROBLEM END ===")

        if IS_LOCAL_RUN:
            save_text_file("TEMP/domain_refined.pddl", domain)
            save_text_file("TEMP/problem_refined.pddl", problem)

        logger.info("🛠️ [Refine] Raffinamento completato.")
        return {
            "refined_domain": domain,
            "refined_problem": problem,
            "domain": domain,
            "problem": problem,
            "error_message": None,
            "refine_count": state.get("refine_count", 0) + 1
        }
    except Exception as err:
        logger.error("❌ Errore nel raffinamento: %s", err, exc_info=True)
        return {
            "refined_domain": None,
            "refined_problem": None,
            "error_message": f"Errore nel raffinamento: {str(err)}"
        }


def end_node(state: PDDLState) -> dict:
    logger.info("✅ [End] Fine della pipeline.")
    return state

# ---------------------
# Costruzione grafo LangGraph
# ---------------------
workflow = StateGraph(PDDLState)
workflow.set_entry_point("BuildPrompt")

workflow.add_node("BuildPrompt", node_build_prompt)
workflow.add_node("GeneratePDDL", node_generate_pddl)
workflow.add_node("Validate", node_validate)
workflow.add_node("Refine", node_refine)
workflow.add_node("End", end_node)

workflow.add_edge("BuildPrompt", "GeneratePDDL")
workflow.add_edge("GeneratePDDL", "Validate")

workflow.add_conditional_edges(
    "Validate",
    path=lambda state: (
        "Refine"
        if state.get("error_message") and state.get("refine_count", 0) < MAX_REFINES
        else "End"
    )
)

workflow.add_conditional_edges(
    "Refine",
    path=lambda state: (
        "Validate" if state.get("refined_domain") else "End"
    )
)

graph = workflow.compile()

# ---------------------
# Test locale
# ---------------------
if __name__ == "__main__":
    LORE_PATH = "lore/example_lore.json"
    with open(LORE_PATH, encoding="utf-8") as f:
        lore_data = json.load(f)

    result = graph.invoke({"lore": lore_data})

    print("\n✅ DOMINIO:\n", result.get("domain", "")[:600])
    print("\n✅ PROBLEMA:\n", result.get("problem", "")[:600])
    print("\n📋 VALIDAZIONE:\n", json.dumps(result.get("validation", {}), indent=2, ensure_ascii=False))

    if result.get("refined_domain"):
        print("\n🔁 Raffinamento eseguito.")
        print("\n🔁 DOMINIO RAFFINATO:\n", result["refined_domain"][:600])
