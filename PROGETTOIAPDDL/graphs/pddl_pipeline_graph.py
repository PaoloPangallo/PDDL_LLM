import os
import json
import logging
import re
from typing import Any, TypedDict, Optional
from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import BaseMessage


from typing import Annotated

from langgraph.graph.message import add_messages

from core.generator import build_prompt_from_lore
from db.db import retrieve_similar_examples_from_db
from core.utils import ask_ollama, extract_between, save_text_file
from core.validator import validate_pddl
from agents.reflection_agent import refine_pddl

logger = logging.getLogger("pddl_pipeline_graph")
logging.basicConfig(level=logging.DEBUG)

# ============================
# 🧠 Stato della pipeline (completo e flessibile)


def safe_add(left, right):
    try:
        return int(left or 0) + int(right or 0)
    except Exception:
        return 0



# Merge strategy: accetta solo l'ultimo valore
def last(_, right):
    return right






class PipelineState(TypedDict):
    lore: dict
    tmp_dir: Annotated[str, last]
    prompt: Annotated[Optional[str], last]
    
    domain: Annotated[Optional[str], last]
    problem: Annotated[Optional[str], last]
    
    validation: Annotated[Optional[dict], last]
    refined_domain: Annotated[Optional[str], last]
    refined_problem: Annotated[Optional[str], last]
    thread_id: Annotated[str, last]


    status: Annotated[str, last]
    error_message: Annotated[Optional[str], last]

    refine_attempts: Annotated[int, safe_add]
    messages: Annotated[list[BaseMessage], add_messages]
    
    


# ============================
# 🚀 Nodi della pipeline
# ============================

from langchain_core.messages import HumanMessage, AIMessage


def node_increment_refine_attempts(state: PipelineState) -> PipelineState:
    """Aggiunge 1 a refine_attempts in modo esplicito."""
    current_attempts = int(state.get("refine_attempts", 0))
    current_attempts += 1
    logger.debug("🔁 refine_attempts incrementato a %d", current_attempts)
    return {**state, "refine_attempts": current_attempts}

def is_positive_feedback(msg: str) -> bool:
    msg = msg.strip().lower()
    return msg in {"ok", "va bene", "accetto", "accetta", "perfetto", "tutto ok", "confermato"}

def node_chat_feedback(state: PipelineState) -> PipelineState:
    """Gestisce il feedback umano e aggiorna i file PDDL, oppure conclude."""
    if not state.get("messages"):
        logger.warning("⏸️ Nessun messaggio umano. Attesa feedback utente.")
        return {**state, "status": "awaiting_feedback"}

    user_msgs = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    if not user_msgs:
        logger.warning("⏸️ Nessun HumanMessage trovato. Attesa feedback.")
        return {**state, "status": "awaiting_feedback"}

    last_msg_content = user_msgs[-1].content #prova a vedere
    last_msg = str(last_msg_content).strip()
    logger.info(f"✍️ Feedback umano ricevuto: {last_msg}")

    if is_positive_feedback(last_msg):
        logger.info("✅ Feedback positivo → fine pipeline.")
        return {
        **state,
        "status": "ok",
        "thread_id": state["thread_id"],
    }

    # Altrimenti: rigenera i file
    domain = state.get("domain", "")
    problem = state.get("problem", "")
    validation = state.get("validation", {})

    prompt = f"""You are a PDDL refinement assistant.
The following feedback was provided by a human:

💬 "{last_msg}"

Here are the current files:

=== DOMAIN START ===
{domain}
=== DOMAIN END ===

=== PROBLEM START ===
{problem}
=== PROBLEM END ===

Validation Summary:
{json.dumps(validation, indent=2)}

Now rewrite both files fixing the issues. Output in the format:
=== DOMAIN START ===
...domain.pddl...
=== DOMAIN END ===
=== PROBLEM START ===
...problem.pddl...
=== PROBLEM END ===
"""

    try:
        logger.info("🧠 Invio prompt a Ollama per rifinitura con feedback umano...")
        response = ask_ollama(prompt)

        rd = extract_between(response, "=== DOMAIN START ===", "=== DOMAIN END ===")
        rp = extract_between(response, "=== PROBLEM START ===", "=== PROBLEM END ===")

        if not rd or not rp:
            raise ValueError("Estrazione fallita: output non ben formattato")

        save_text_file(os.path.join(state["tmp_dir"], "domain_refined.pddl"), rd)
        save_text_file(os.path.join(state["tmp_dir"], "problem_refined.pddl"), rp)

        return {
            **state,
            "domain": rd,
            "problem": rp,
            "refined_domain": rd,
            "refined_problem": rp,
            "status": "ok",
            "messages": state["messages"] + [AIMessage(content=response)]
        }

    except Exception as e:
        logger.error("❌ [ChatFeedback] %s", e, exc_info=True)
        return {
            **state,
            "status": "failed",
            "error_message": f"ChatFeedback error: {str(e)}",
            "thread_id": state["thread_id"],
}





def clean_code_blocks(text: str) -> str:
    """Rimuove blocchi markdown tipo ```lang\n...``` o ```...``` intorno al codice"""
    return re.sub(r"```(?:[a-zA-Z]+\n)?(.*?)```", r"\1", text, flags=re.DOTALL)

import shutil

def node_build_prompt(state: PipelineState) -> PipelineState:
    # invece di usare tempfile, pointiamo a static/uploads/<thread_id>
    thread_id = state.get("thread_id", "default")
    upload_dir = os.path.join("static", "uploads", thread_id)
    # puliamo / ricreiamo la cartella
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir)
    os.makedirs(upload_dir, exist_ok=True)
    logger.debug("🧠 [BuildPrompt] upload_dir creato: %s", upload_dir)

    # costruiamo il prompt come prima
    examples_raw = retrieve_similar_examples_from_db(state["lore"], k=1)
    examples = [str(e) for e in examples_raw if isinstance(e, str)]
    prompt, _ = build_prompt_from_lore(state["lore"], examples=examples)

    return {
        **state,
        "tmp_dir": upload_dir,   # ora punta a static/uploads/<thread_id>
        "prompt": prompt,
        "status": "ok"
    }


def node_generate_pddl(state: PipelineState) -> PipelineState:
    if state.get("status") != "ok":
        logger.warning("⚠️ Skipping generate due to status != ok")
        return {**state, "status": "failed", "error_message": "Skipped generate (bad status)"}

    try:
        prompt = state["prompt"] or ""
        response = ask_ollama(prompt)
        tmp_dir = state["tmp_dir"]

        raw_path = os.path.join(tmp_dir, "raw_response.txt")
        save_text_file(raw_path, response)
        logger.info(f"📄 Risposta grezza salvata in: {raw_path}")

        logger.debug("📟 Prompt usato:\n%s", state["prompt"])
        logger.debug("📨 Risposta grezza (primi 300):\n%s", response[:300])

        domain_raw = extract_between(response, "=== DOMAIN START ===", "=== DOMAIN END ===")
        problem_raw = extract_between(response, "=== PROBLEM START ===", "=== PROBLEM END ===")

        if not domain_raw or not problem_raw:
            logger.warning("⚠️ Dominio o problema non trovati nell'output.")
            logger.debug("💬 Output ricevuto:\n%s", response)
            raise ValueError("Dominio o problema non trovati nel formato atteso")

        domain = clean_code_blocks(domain_raw)
        problem = clean_code_blocks(problem_raw)

        domain_path = os.path.join(tmp_dir, "domain.pddl")
        problem_path = os.path.join(tmp_dir, "problem.pddl")
        save_text_file(domain_path, domain)
        save_text_file(problem_path, problem)


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

def node_validate(state: PipelineState) -> PipelineState:
    logger.debug("📦 [Validate] Stato ricevuto:")
    
    if state.get("status") != "ok":
        return {**state, "status": "failed", "error_message": "Skipped validate"}

    try:
        # 🔁 Usa i refined se presenti
        domain = state.get("refined_domain") or state.get("domain") or ""
        problem = state.get("refined_problem") or state.get("problem") or ""

        source = "refined" if state.get("refined_domain") else "original"
        logger.info(f"🔍 Validazione su file: {source}")

        validation = validate_pddl(domain, problem, state["lore"])
        valid_syntax = validation.get("valid_syntax", False)
        semantic_errors = validation.get("semantic_errors", [])
        status = "ok" if valid_syntax and not semantic_errors else "failed"
        err_msg = None if status == "ok" else "Validation errors"

        logger.debug("📋 [Validate] %s", json.dumps(validation, indent=2))
        all_validations = state.get("all_validations", [])
        return {
            **state,
            "validation": validation,
            "all_validations": all_validations + [validation], # type: ignore
            "status": status,
            "error_message": err_msg,
        }

    except Exception as e:
        logger.error("❌ [Validate] Errore: %s", e, exc_info=True)
        return {
            **state,
            "status": "failed",
            "error_message": str(e)
        }


def node_refine(state: PipelineState) -> PipelineState:
    if state.get("status") != "failed":
        logger.debug("✅ [Refine] Stato OK, skip refine.")
        return {**state, "status": "ok"}

    if not state.get("tmp_dir"):
        logger.warning("⚠️ [Refine] tmp_dir mancante, impossibile procedere.")
        return {
            **state,
            "status": "failed",
            "error_message": "Missing tmp_dir for refine"
        }

    try:
        logger.debug("🔧 [Refine] Avvio refine con error: %s", state.get("error_message", ""))
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

        logger.info("✅ [Refine] Raffinamento completato con successo.")
        return {
    **state,
    "refined_domain": rd,
    "refined_problem": rp,
    "status": "ok",
    "thread_id": state["thread_id"],
}


    except Exception as e:
        logger.error("❌ [Refine] Errore durante il refine: %s", str(e), exc_info=True)
        return {
    **state,
    "status": "failed",
    "error_message": str(e),
    "thread_id": state["thread_id"],
}

### ciao

def end_node(state: PipelineState) -> PipelineState:
    logger.debug("✅ [End] state finale: %s", state)
    out: PipelineState = {
        "prompt":  state.get("prompt"),
        "tmp_dir": state.get("tmp_dir"),
    }
    for key in ("domain", "problem", "validation", "error_message", "refined_domain", "refined_problem"):
        if key in state:
            out[key] = state[key]
    return out



# ============================
# 🔄 Controllo branching
# ============================

def validate_branching_logic(state: PipelineState) -> dict[str, Any]:
    # Se è già OK → End
    if state.get("status") == "ok":
        return {"next": "End", "state": state}

    # Normalizziamo refine_attempts
    try:
        ra = int(state.get("refine_attempts", 0))
    except:
        ra = 0
    ra = max(0, min(ra, 100))
    state["refine_attempts"] = ra

    # Se non abbiamo ancora fatto due refine automatici → Refine
    if ra < 2:
        return {
            "next": "Refine",
            "state": { **state, "status": "start_refine" }
        }

    # Altrimenti (2 o più refine già tentati) → ChatFeedback
    return {
        "next": "ChatFeedback",
        "state": { **state, "status": "awaiting_feedback" }
    }



def should_continue_after_refine(state: PipelineState) -> dict[str, Any]:
    user_msgs = [m for m in state.get("messages", []) if isinstance(m, HumanMessage)]
    if user_msgs:
        last_msg = user_msgs[-1].content.strip().lower()
        if last_msg in {"ok", "accetto", "va bene", "perfetto"}:
            return {
                "next": "End",
                "state": {**state, "status": "ok", "thread_id": state["thread_id"]}
            }

    # 🔁 Se non è "ok", vai a Refine
    return {
        "next": "Refine",
        "state": {**state, "status": "start_refine", "thread_id": state["thread_id"]}
    }



# ============================
# ⚙️ Costruzione grafo
# ============================
def build_pipeline(checkpointer=None):
    builder = StateGraph(PipelineState, stateful=True)

    # Nodi
    builder.add_node("BuildPrompt", node_build_prompt)
    builder.add_node("Generate", node_generate_pddl)
    builder.add_node("Validate", node_validate)
    builder.add_node("Refine", node_refine)
    builder.add_node("IncrementRefineAttempts", node_increment_refine_attempts)  # ← nuovo nodo
    builder.add_node("ChatFeedback", node_chat_feedback)
    builder.add_node("End", end_node)

    # Flusso principale
    builder.set_entry_point("BuildPrompt")
    builder.add_edge("BuildPrompt", "Generate")
    builder.add_edge("Generate", "Validate")

    # Validate → Refine o End (condizionale)
    builder.add_edge("Validate", "Refine")
    builder.add_edge("Validate", "End")
    builder.add_conditional_edges("Validate", path=validate_branching_logic)

    # Refine → IncrementRefineAttempts → ChatFeedback
    # Refine → IncrementRefineAttempts → Validate (ripeti validazione sui PDDL raffinati)
    builder.add_edge("Refine", "IncrementRefineAttempts")
    builder.add_edge("IncrementRefineAttempts", "Validate")


    # ChatFeedback → End o Refine (in base a should_continue_after_refine)
    builder.add_edge("ChatFeedback", "End")
    builder.add_conditional_edges("ChatFeedback", path=should_continue_after_refine)

    # Compilazione
    return builder.compile(checkpointer=checkpointer) if checkpointer else builder.compile()



import sqlite3

logger = logging.getLogger("pddl_pipeline_graph")

def get_pipeline_with_memory(thread_id: str, reset: bool = False):
    logger.info(f"🧠 Pipeline persistente per thread: {thread_id}")

    abs_path = os.path.abspath(f"memory/{thread_id}.sqlite")
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    # ✅ Reset: cancella completamente la memoria
    if reset and os.path.exists(abs_path):
        os.remove(abs_path)
        logger.warning(f"🧹 File di memoria rimosso per reset: {abs_path}")

    # ✅ Connessione nuova e saver isolato
    conn = sqlite3.connect(abs_path, check_same_thread=False)
    saver = SqliteSaver(conn)

    # ✅ Svuota tabelle se esistono (in caso il file esista ma non venga cancellato correttamente)
    if reset:
        with conn:
            conn.execute("DROP TABLE IF EXISTS state")
            conn.execute("DROP TABLE IF EXISTS checkpoints")

    # ✅ Costruisci sempre la pipeline
    pipeline = build_pipeline(checkpointer=saver)
    return pipeline.with_config(configurable={"thread_id": thread_id})



__all__ = ["get_pipeline_with_memory"]
