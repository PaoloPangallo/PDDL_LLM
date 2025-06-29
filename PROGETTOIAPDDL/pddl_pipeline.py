from langgraph.graph import StateGraph
from typing import TypedDict, Optional
# from langgraph.checkpoint.memory import MemorySaver  # Non usato

from game.generator import build_prompt_from_lore
from game.utils import ask_ollama, extract_between, save_text_file
from game.validator import validate_pddl
from agent.reflection_agent import refine_pddl

import os
import logging

# ---------------------
# Logging setup
# ---------------------
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

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
# Nodi
# ---------------------
def node_build_prompt(state: PDDLState) -> dict:
    logger.debug("🧠 [BuildPrompt] Lore ricevuto:\n%s", state["lore"])
    prompt, _ = build_prompt_from_lore(state["lore"])
    logger.debug("📝 [BuildPrompt] Prompt costruito:\n%s", prompt[:300])
    return {"prompt": prompt}

def node_generate_pddl(state: PDDLState) -> dict:
    try:
        logger.debug("🤖 [GeneratePDDL] Invio a Ollama...")
        response = ask_ollama(state["prompt"])
        domain = extract_between(response, "=== DOMAIN START ===", "=== DOMAIN END ===")
        problem = extract_between(response, "=== PROBLEM START ===", "=== PROBLEM END ===")

        if not domain or not problem:
            raise ValueError("Estrazione dominio o problema fallita")

        os.makedirs("TEMP", exist_ok=True)
        save_text_file("TEMP/domain.pddl", domain)
        save_text_file("TEMP/problem.pddl", problem)

        logger.debug("✅ [GeneratePDDL] Dominio e problema generati con successo.")
        return {"domain": domain, "problem": problem}
    except Exception as e:
        logger.error("❌ Errore in node_generate_pddl: %s", e, exc_info=True)
        return {"domain": None, "problem": None, "error_message": str(e)}

def node_validate(state: PDDLState) -> dict:
    domain = state.get("domain")
    problem = state.get("problem")
    lore = state.get("lore", {})

    if not domain or not problem:
        return {
            "validation": None,
            "error_message": "Missing domain or problem for validation."
        }

    try:
        validation = validate_pddl(domain, problem, lore)
        logger.debug("📋 [Validate] Risultato validazione:\n%s", validation)

        if not validation.get("valid_syntax", False):
            return {"validation": validation, "error_message": "Invalid PDDL syntax."}

        return {"validation": validation, "error_message": None}
    except Exception as e:
        logger.error("❌ Errore durante la validazione: %s", e, exc_info=True)
        return {"validation": None, "error_message": f"Errore nella validazione: {str(e)}"}

def node_refine(state: PDDLState) -> dict:
    try:
        lore = state.get("lore", {})
        logger.debug("🔁 [Refine] Avvio raffinamento con messaggio: %s", state.get("error_message"))

        refined = refine_pddl(
            domain_path="TEMP/domain.pddl",
            problem_path="TEMP/problem.pddl",
            error_message=state["error_message"],
            lore=lore
        )

        domain = extract_between(refined, "=== DOMAIN START ===", "=== DOMAIN END ===")
        problem = extract_between(refined, "=== PROBLEM START ===", "=== PROBLEM END ===")

        save_text_file("TEMP/domain_refined.pddl", domain)
        save_text_file("TEMP/problem_refined.pddl", problem)

        logger.debug("🛠️ [Refine] Raffinamento completato.")
        return {
            "refined_domain": domain,
            "refined_problem": problem,
            "domain": domain,
            "problem": problem,
            "error_message": None
        }
    except Exception as e:
        logger.error("❌ Errore nel raffinamento: %s", e, exc_info=True)
        return {
            "refined_domain": None,
            "refined_problem": None,
            "error_message": f"Errore nel raffinamento: {str(e)}"
        }

# ---------------------
# Grafo (senza memory)
# ---------------------
workflow = StateGraph(PDDLState)
workflow.add_node("BuildPrompt", node_build_prompt)
workflow.add_node("GeneratePDDL", node_generate_pddl)
workflow.add_node("Validate", node_validate)
workflow.add_node("Refine", node_refine)

workflow.set_entry_point("BuildPrompt")
workflow.add_edge("BuildPrompt", "GeneratePDDL")
workflow.add_edge("GeneratePDDL", "Validate")

# Flusso condizionale: se c'è errore → Refine, altrimenti fine
workflow.add_conditional_edges(
    "Validate",
    path=lambda state: "Refine" if state.get("error_message") else None
)

graph = workflow.compile()

# ---------------------
# Test locale
# ---------------------
if __name__ == "__main__":
    import json
    lore_path = "lore/example_lore.json"
    lore = json.load(open(lore_path, encoding="utf-8"))

    result = graph.invoke({"lore": lore})

    print("\n✅ DOMINIO:\n", result["domain"][:600])
    print("\n✅ PROBLEMA:\n", result["problem"][:600])
    print("\n📋 VALIDAZIONE:\n", json.dumps(result["validation"], indent=2, ensure_ascii=False))
    if result.get("refined_domain"):
        print("\n🔁 È stato eseguito un raffinamento con successo.")
