import os
import json
import logging
import re
from typing import TypedDict, Optional
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
    """Segnala che refine_attempts deve essere incrementato di 1."""
    logger.debug("🔁 refine_attempts incrementato di +1")
    return {"refine_attempts": 1}


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

    last_msg = user_msgs[-1].content.strip()
    logger.info(f"✍️ Feedback umano ricevuto: {last_msg}")

    # Caso 1: feedback positivo → si termina
    if is_positive_feedback(last_msg):
        logger.info("✅ Feedback positivo → fine pipeline.")
        return {
            **state,
            "status": "ok",
        }

    # Caso 2: feedback negativo → genera nuovo prompt di refine
    domain = state.get("refined_domain") or state.get("domain")
    problem = state.get("refined_problem") or state.get("problem")
    validation = state.get("validation", {})

    if not domain or not problem:
        logger.error("❌ Domain/problem non presenti. Non posso rigenerare.")
        return {
            **state,
            "status": "failed",
            "error_message": "Missing domain/problem for ChatFeedback",
        }

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

        rd = extract_between(response, "=== DOMAIN START ===", "=== DOMAIN END ===").strip()
        rp = extract_between(response, "=== PROBLEM START ===", "=== PROBLEM END ===").strip()

        if not rd or not rp:
            raise ValueError("Estrazione fallita: output non ben formattato")

        save_text_file(os.path.join(state["tmp_dir"], "domain_refined.pddl"), rd)
        save_text_file(os.path.join(state["tmp_dir"], "problem_refined.pddl"), rp)

        return {
            **state,
            "refined_domain": rd,
            "refined_problem": rp,
            "status": "failed",  
            "error_message": "New version from ChatFeedback generated",
            "messages": state["messages"] + [AIMessage(content=response)]
        }

    except Exception as e:
        logger.error("❌ [ChatFeedback] %s", e, exc_info=True)
        return {
            **state,
            "status": "failed",
            "error_message": f"ChatFeedback error: {str(e)}"
        }






def clean_code_blocks(text: str) -> str:
    """Rimuove blocchi markdown tipo ```lang\n...``` o ```...``` intorno al codice"""
    return re.sub(r"```(?:[a-zA-Z]+\n)?(.*?)```", r"\1", text, flags=re.DOTALL)

import shutil

def node_build_prompt(state: PipelineState) -> PipelineState:
    # Se già esiste il prompt o i file, evitiamo di sovrascrivere
    if state.get("prompt") and state.get("tmp_dir") and os.path.exists(state["tmp_dir"]):
        logger.warning("⚠️ [BuildPrompt] Nodo invocato ma prompt già presente. Skip.")
        return state

    thread_id = state.get("thread_id", "default")
    upload_dir = os.path.join("static", "uploads", thread_id)

    # Pulisci solo se è una prima esecuzione (o la cartella è incoerente)
    if not os.path.exists(upload_dir) or not os.listdir(upload_dir):
        if os.path.exists(upload_dir):
            shutil.rmtree(upload_dir)
        os.makedirs(upload_dir, exist_ok=True)
        logger.debug("🧠 [BuildPrompt] upload_dir creato: %s", upload_dir)
    else:
        logger.warning("📁 [BuildPrompt] upload_dir già esistente e non vuoto: %s", upload_dir)

    # Costruzione prompt
    examples_raw = retrieve_similar_examples_from_db(state["lore"], k=1)
    examples = [e for e in examples_raw if isinstance(e, str)]
    prompt, _ = build_prompt_from_lore(state["lore"], examples=examples)

    return {
        **state,
        "tmp_dir": upload_dir,
        "prompt": prompt,
        "status": "ok"
    }


def node_generate_pddl(state: PipelineState) -> PipelineState:
    if state.get("status") != "ok":
        logger.warning("⚠️ Skipping generate due to status != ok")
        return {**state, "status": "failed", "error_message": "Skipped generate (bad status)"}

    try:
        response = ask_ollama(state["prompt"])
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
    logger.debug("📦 [Validate] Stato ricevuto.")

    try:
        # 🔁 Usa i refined se presenti
        domain = state.get("refined_domain") or state.get("domain")
        problem = state.get("refined_problem") or state.get("problem")

        # ⚠️ Check difensivo
        if not domain or not problem:
            logger.warning("⚠️ File domain/problem mancanti. Impossibile validare.")
            return {
                **state,
                "status": "failed",
                "error_message": "Missing domain or problem for validation"
            }

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
            "all_validations": all_validations + [validation],
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
    # Se i file raffinati già esistono, salta il refine
    if state.get("refined_domain") and state.get("refined_problem"):
        logger.debug("✅ [Refine] Refinement già effettuato, skip.")
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

        rd = extract_between(updated, "=== DOMAIN START ===", "=== DOMAIN END ===").strip()
        rp = extract_between(updated, "=== PROBLEM START ===", "=== PROBLEM END ===").strip()

        save_text_file(os.path.join(state["tmp_dir"], "domain_refined.pddl"), rd)
        save_text_file(os.path.join(state["tmp_dir"], "problem_refined.pddl"), rp)

        logger.info("✅ [Refine] Raffinamento completato con successo.")
        return {
            **state,
            "refined_domain": rd,
            "refined_problem": rp,
            "status": "ok",
        }

    except Exception as e:
        logger.error("❌ [Refine] Errore durante il refine: %s", str(e), exc_info=True)
        return {
            **state,
            "status": "failed",
            "error_message": str(e),
        }


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

def validate_branching_logic(state: PipelineState) -> str:
    validation = state.get("validation", {})
    refine_attempts = int(state.get("refine_attempts", 0))

    if validation.get("valid_syntax", False):
        return "End"
    
    # Primo o secondo refine → ancora permesso
    if refine_attempts < 2:
        return "Refine"
    
    # Già fatti 2 refine → ora attendo feedback umano
    return "ChatFeedback"




def should_continue_after_refine(state: PipelineState) -> str:
    user_msgs = [m for m in state.get("messages", []) if isinstance(m, HumanMessage)]
    if user_msgs:
        last_msg = user_msgs[-1].content.strip().lower()
        if last_msg in {"ok", "accetto", "va bene", "perfetto"}:
            return "End"
    return "Refine"




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
    builder.add_node("IncrementRefineAttempts", node_increment_refine_attempts)
    builder.add_node("ChatFeedback", node_chat_feedback)
    builder.add_node("End", end_node)

    # Flusso principale
    builder.set_entry_point("BuildPrompt")
    builder.add_edge("BuildPrompt", "Generate")
    builder.add_edge("Generate", "Validate")

    # Validazione → Refine | ChatFeedback | End
    builder.add_conditional_edges("Validate", path=validate_branching_logic)

    # Refine → Increment → Validate (ri-validazione)
    builder.add_edge("Refine", "IncrementRefineAttempts")
    builder.add_edge("IncrementRefineAttempts", "Validate")

    # ChatFeedback → Refine | End (basato su input utente)
    builder.add_conditional_edges("ChatFeedback", path=should_continue_after_refine)

    return builder.compile(checkpointer=checkpointer) if checkpointer else builder.compile()



import sqlite3

llogger = logging.getLogger("pddl_pipeline_graph")

def get_pipeline_with_memory(thread_id: str, reset: bool = True):
    """
    Restituisce una pipeline LangGraph con memoria persistente per il thread dato.

    Args:
        thread_id (str): identificatore univoco del thread (es. session-1)
        reset (bool): se True, cancella la memoria precedente

    Returns:
        LangGraph pipeline configurata con salvataggio SQLite
    """
    logger.info(f"🧠 Pipeline persistente per thread: {thread_id}")

    db_path = os.path.abspath(f"memory/{thread_id}.sqlite")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # ✅ Cancellazione file se richiesto
    if reset and os.path.exists(db_path):
        os.remove(db_path)
        logger.warning(f"🧹 File di memoria eliminato per reset: {db_path}")

    # ✅ Connessione e inizializzazione SQLite
    conn = sqlite3.connect(db_path, check_same_thread=False)
    saver = SqliteSaver(conn)

    # ✅ Pulizia interna delle tabelle, in caso di file parzialmente corrotto
    if reset:
        try:
            with conn:
                conn.execute("DROP TABLE IF EXISTS state")
                conn.execute("DROP TABLE IF EXISTS checkpoints")
                logger.debug("🧼 Tabelle SQLite rimosse (state, checkpoints)")
        except Exception as e:
            logger.error(f"❌ Errore durante il reset delle tabelle: {e}")

    # ✅ Diagnostica: verifica esistenza checkpoint
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='checkpoints'")
        table_exists = cursor.fetchone()[0] > 0

        if table_exists:
            cursor.execute("SELECT COUNT(*) FROM checkpoints")
            checkpoint_count = cursor.fetchone()[0]
            logger.info(f"💾 Checkpoints esistenti: {checkpoint_count}")
        else:
            logger.info("📭 Nessuna tabella checkpoints presente. Partenza da zero.")
    except Exception as e:
        logger.warning(f"⚠️ Errore nel controllo stato del database: {e}")

    # ✅ Costruzione pipeline con checkpointer
    pipeline = build_pipeline(checkpointer=saver)
    return pipeline.with_config(configurable={"thread_id": thread_id})

__all__ = ["get_pipeline_with_memory"]
