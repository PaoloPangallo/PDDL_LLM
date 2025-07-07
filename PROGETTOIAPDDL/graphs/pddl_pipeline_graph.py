import os
import json
import logging
import re
import tempfile
from typing import TypedDict, Optional, Union
from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
from core.generator import build_prompt_from_lore
from db.db import retrieve_similar_examples_from_db
from core.utils import ask_ollama, extract_between, save_text_file
from core.validator import validate_pddl
from agents.reflection_agent import refine_pddl

logger = logging.getLogger("pddl_pipeline_graph")
logging.basicConfig(level=logging.DEBUG)

# ============================
# 🔢 Stato della pipeline
# ============================
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

# ============================
# 🚀 Nodi della pipeline
# ============================

def clean_code_blocks(text: str) -> str:
    """Rimuove blocchi markdown tipo ```lang\n...``` o ```...``` intorno al codice"""
    return re.sub(r"```(?:[a-zA-Z]+\n)?(.*?)```", r"\1", text, flags=re.DOTALL)

def node_build_prompt(state: InputState) -> dict:
    tmp_dir = tempfile.mkdtemp(prefix="pddl_")
    logger.debug("🧠 [BuildPrompt] tmp_dir creato: %s", tmp_dir)

    examples_raw = retrieve_similar_examples_from_db(state["lore"], k=1)
    examples = [e for e in examples_raw if isinstance(e, str)]
    prompt, _ = build_prompt_from_lore(state["lore"], examples=examples)

    logger.debug("📚 [BuildPrompt] Prompt (prime 300 char): %s", prompt[:300])
    return {
        **state,
        "tmp_dir": tmp_dir,
        "prompt": prompt,
        "status": "ok"
    }

def node_generate_pddl(state: InputState) -> dict:
    if state.get("status") != "ok":
        logger.warning("⚠️ Skipping generate due to status != ok")
        return {**state, "status": "failed", "error_message": "Skipped generate (bad status)"}

    try:
        response = ask_ollama(state["prompt"])
        tmp_dir = state["tmp_dir"]

        # ✅ Salva SEMPRE la risposta grezza per analisi
        raw_path = os.path.join(tmp_dir, "raw_response.txt")
        save_text_file(raw_path, response)
        logger.info(f"📄 Risposta grezza salvata in: {raw_path}")

        logger.debug("🧾 Prompt usato:\n%s", state["prompt"])
        logger.debug("📨 Risposta grezza (primi 300):\n%s", response[:300])

        # ⛏️ Estrai i blocchi PDDL dal testo grezzo
        domain_raw = extract_between(response, "=== DOMAIN START ===", "=== DOMAIN END ===")
        problem_raw = extract_between(response, "=== PROBLEM START ===", "=== PROBLEM END ===")

        if not domain_raw or not problem_raw:
            logger.warning("⚠️ Dominio o problema non trovati nell'output.")
            logger.debug("💬 Output ricevuto:\n%s", response)
            raise ValueError("Dominio o problema non trovati nel formato atteso")

        # 🧼 Pulisci eventuali backtick Markdown
        domain = clean_code_blocks(domain_raw)
        problem = clean_code_blocks(problem_raw)

        # 💾 Salva i file PDDL
        domain_path = os.path.join(tmp_dir, "domain.pddl")
        problem_path = os.path.join(tmp_dir, "problem.pddl")
        save_text_file(domain_path, domain)
        save_text_file(problem_path, problem)

        logger.info(f"✅ File salvati: {domain_path}, {problem_path}")

        return {
            **state,
            "domain": domain,
            "problem": problem,
            "status": "ok"
        }

    except Exception as e:
        logger.error("❌ [GeneratePDDL] %s", e, exc_info=True)
        return {
            **state,
            "domain": "",
            "problem": "",
            "status": "failed",
            "error_message": f"GeneratePDDL error: {str(e)}"
        }


def node_validate(state: InputState) -> dict:
    logger.debug("📦 Stato ricevuto da GeneratePDDL:")
    logger.debug(json.dumps(state, indent=2, ensure_ascii=False))
    if state.get("status") != "ok":
        return {**state, "status": "failed", "error_message": "Skipped validate"}

    try:
        validation = validate_pddl(state["domain"], state["problem"], state["lore"])
        valid_syntax = validation.get("valid_syntax", False)
        sem_err = validation.get("semantic_errors", [])
        status = "ok" if valid_syntax and not sem_err else "failed"
        err_msg = None if status == "ok" else "Validation errors"

        logger.debug("📋 [Validate] %s", json.dumps(validation, indent=2))
        return {
            **state,
            "validation": validation,
            "status": status,
            "error_message": err_msg
        }
    except Exception as e:
        logger.error("❌ [Validate] %s", e, exc_info=True)
        return {
            **state,
            "status": "failed",
            "error_message": str(e)
        }

def node_refine(state: InputState) -> dict:
    if state.get("status") != "failed":
        return {**state, "status": "ok"}  # skip refine

    if not state.get("tmp_dir"):
        logger.warning("⚠️ [Refine] tmp_dir mancante, impossibile procedere.")
        return {**state, "status": "failed", "error_message": "Missing tmp_dir for refine"}

    try:
        updated = refine_pddl(
            domain_path=os.path.join(state["tmp_dir"], "domain.pddl"),
            problem_path=os.path.join(state["tmp_dir"], "problem.pddl"),
            error_message=state.get("error_message", ""),
            lore=state["lore"]
        )
        rd = extract_between(updated, "=== DOMAIN START ===", "=== DOMAIN END ===")
        rp = extract_between(updated, "=== PROBLEM START ===", "=== PROBLEM END ===")

        save_text_file(os.path.join(state["tmp_dir"], "domain_refined.pddl"), rd)
        save_text_file(os.path.join(state["tmp_dir"], "problem_refined.pddl"), rp)

        return {
            **state,
            "refined_domain": rd,
            "refined_problem": rp,
            "status": "ok"
        }
    except Exception as e:
        logger.error("❌ [Refine] %s", e, exc_info=True)
        return {
            **state,
            "status": "failed",
            "error_message": str(e)
        }

def end_node(state: InputState) -> dict:
    logger.debug("✅ [End] state finale: %s", state)
    out: OutputState = {}
    for key in ("domain", "problem", "validation", "error_message", "refined_domain", "refined_problem"):
        if key in state:
            out[key] = state[key]
    return out

# ============================
# 🔄 Controllo branching
# ============================
def should_refine(state: InputState) -> str:
    if state.get("status") == "ok" and state.get("validation", {}).get("valid_syntax", False):
        return "End"
    return "Refine"

# ============================
# ⚙️ Costruzione grafo
# ============================
def build_pipeline():
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
    builder.add_edge("Refine", "End")

    return builder.compile()

def get_pipeline_with_memory(thread_id: str):
    logger.info(f"🧠 Pipeline persistente per thread: {thread_id}")
    logger.info(f"📍 Salvataggio in: memory/{thread_id}.sqlite")

    os.makedirs("memory", exist_ok=True)
    saver = SqliteSaver.from_conn_string(f"sqlite:///memory/{thread_id}.sqlite")
    return build_pipeline().with_config(checkpointer=saver)

__all__ = ["get_pipeline_with_memory"]
