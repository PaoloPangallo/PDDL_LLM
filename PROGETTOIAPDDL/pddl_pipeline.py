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
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("PDDL_Pipeline")

# ---------------------
# Stato del flusso
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
# Nodi della pipeline
# ---------------------
def node_build_prompt(state: PDDLState) -> dict:
    """Costruisce il prompt da lore e include esempi simili dal DB (RAG)."""
    logger.debug("BuildPrompt — lore keys: %s", list(state["lore"].keys()))
    examples_raw = retrieve_similar_examples_from_db(state["lore"], k=1)
    examples = [e for e in examples_raw if isinstance(e, str)]
    if examples:
        logger.debug("BuildPrompt — recuperati %d esempi simili", len(examples))
    else:
        logger.debug("BuildPrompt — nessun esempio simile trovato")
    prompt, _ = build_prompt_from_lore(state["lore"], examples=examples)
    logger.debug("BuildPrompt — prompt (troncato): %s", prompt[:200].replace("\n"," "))
    return {"prompt": prompt}


def node_generate_pddl(state: PDDLState) -> dict:
    """Genera dominio e problema PDDL a partire dal prompt."""
    try:
        logger.debug("GeneratePDDL — invio a Ollama")
        response = ask_ollama(state["prompt"])
        domain = extract_between(response, "=== DOMAIN START ===", "=== DOMAIN END ===")
        problem = extract_between(response, "=== PROBLEM START ===", "=== PROBLEM END ===")
        if not domain or not problem:
            raise ValueError("Estrazione dominio o problema fallita")

        os.makedirs("TEMP", exist_ok=True)
        save_text_file("TEMP/domain.pddl", domain)
        save_text_file("TEMP/problem.pddl", problem)
        logger.info("GeneratePDDL — dominio e problema generati e salvati in TEMP/")
        return {"domain": domain, "problem": problem, "error_message": None}
    except Exception as err:
        logger.error("GeneratePDDL — errore: %s", err, exc_info=True)
        return {"domain": None, "problem": None, "error_message": str(err)}


def node_validate(state: PDDLState) -> dict:
    """Valida i file PDDL usando il contenuto della lore."""
    domain = state.get("domain")
    problem = state.get("problem")
    if not domain or not problem:
        msg = "Mancano dominio o problema per la validazione"
        logger.warning("Validate — %s", msg)
        return {"validation": None, "error_message": msg}

    try:
        validation = validate_pddl(domain, problem, state["lore"])
        logger.debug("Validate — raw validation: %s", validation)

        # Controllo sintassi
        if not validation.get("valid_syntax", False):
            msg = "Sintassi PDDL non valida"
            logger.warning("Validate — %s", msg)
            return {"validation": validation, "error_message": msg}

        # Controlli semantici
        issues = []
        if validation.get("undefined_objects_in_goal"):
            count = len(validation["undefined_objects_in_goal"])
            issues.append(f"{count} oggetti non definiti nel goal")
        if validation.get("undefined_actions"):
            count = len(validation["undefined_actions"])
            issues.append(f"{count} azioni non definite")
        if validation.get("semantic_errors"):
            count = len(validation["semantic_errors"])
            issues.append(f"{count} errori semantici")
        if issues:
            msg = "; ".join(issues)
            logger.warning("Validate — problemi semantici: %s", msg)
            return {"validation": validation, "error_message": msg}

        logger.info("Validate — PDDL valido sintatticamente e semanticamente")
        return {"validation": validation, "error_message": None}

    except Exception as err:
        msg = f"Errore durante la validazione: {err}"
        logger.error("Validate — %s", msg, exc_info=True)
        return {"validation": None, "error_message": msg}


def node_refine(state: PDDLState) -> dict:
    """Raffina i file PDDL in base agli errori emersi."""
    try:
        logger.debug("Refine — avvio con error_message: %s", state.get("error_message"))
        refined = refine_pddl(
            domain_path="TEMP/domain.pddl",
            problem_path="TEMP/problem.pddl",
            error_message=state["error_message"],
            lore=state["lore"]
        )
        domain = extract_between(refined, "=== DOMAIN START ===", "=== DOMAIN END ===")
        problem = extract_between(refined, "=== PROBLEM START ===", "=== PROBLEM END ===")

        save_text_file("TEMP/domain_refined.pddl", domain)
        save_text_file("TEMP/problem_refined.pddl", problem)
        logger.info("Refine — raffinamento completato e file salvati")
        return {
            "refined_domain": domain,
            "refined_problem": problem,
            "domain": domain,
            "problem": problem,
            "error_message": None
        }
    except Exception as err:
        msg = f"Errore nel raffinamento: {err}"
        logger.error("Refine — %s", msg, exc_info=True)
        return {
            "refined_domain": None,
            "refined_problem": None,
            "error_message": msg
        }


def end_node(state: PDDLState) -> dict:
    """Nodo terminale: ritorna lo stato finale."""
    logger.info("End — fine del workflow")
    return state

# ---------------------
# Costruzione del grafo LangGraph
# ---------------------
workflow = StateGraph(PDDLState)
workflow.add_node("BuildPrompt", node_build_prompt)
workflow.add_node("GeneratePDDL", node_generate_pddl)
workflow.add_node("Validate", node_validate)
workflow.add_node("Refine", node_refine)
workflow.add_node("End", end_node)

workflow.set_entry_point("BuildPrompt")
workflow.add_edge("BuildPrompt", "GeneratePDDL")
workflow.add_edge("GeneratePDDL", "Validate")
workflow.add_conditional_edges(
    "Validate",
    path=lambda state: "Refine" if state.get("error_message") else "End"
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

    print("\n✅ DOMINIO:\n", result["domain"][:600])
    print("\n✅ PROBLEMA:\n", result["problem"][:600])
    print("\n📋 VALIDAZIONE:\n", json.dumps(result["validation"], indent=2, ensure_ascii=False))
    if result.get("refined_domain"):
        print("\n🔁 È stato eseguito un raffinamento con successo.")
        print("\n🔁 DOMINIO RAFFINATO:\n", result["refined_domain"][:600])
