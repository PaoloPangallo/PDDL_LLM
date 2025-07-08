import os
import json
import logging
import re
import tempfile
from typing import Any, List, TypedDict, Optional
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


    status: Annotated[str, last]
    error_message: Annotated[Optional[str], last]

    refine_attempts: Annotated[int, int.__add__]  # oppure operator.add
    messages: Annotated[list[BaseMessage], add_messages]
    
    


# ============================
# 🚀 Nodi della pipeline
# ============================

from langchain_core.messages import HumanMessage, AIMessage

def node_chat_feedback(state: PipelineState) -> PipelineState:
    """Gestisce il feedback umano e aggiorna i file PDDL."""
    if not state.get("messages"):
        logger.warning("⚠️ Nessun messaggio umano disponibile.")
        return {**state, "status": "failed", "error_message": "Manca il messaggio umano."}

    # Recupera ultimo messaggio umano
    user_msgs = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    if not user_msgs:
        logger.warning("⚠️ Nessun HumanMessage trovato in messages.")
        return {**state, "status": "failed", "error_message": "Nessun HumanMessage in stato."}

    last_msg = user_msgs[-1].content
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
            "error_message": f"ChatFeedback error: {str(e)}"
        }



def clean_code_blocks(text: str) -> str:
    """Rimuove blocchi markdown tipo ```lang\n...``` o ```...``` intorno al codice"""
    return re.sub(r"```(?:[a-zA-Z]+\n)?(.*?)```", r"\1", text, flags=re.DOTALL)

def node_build_prompt(state: PipelineState) -> PipelineState:
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

def node_validate(state: PipelineState) -> PipelineState:
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

def node_refine(state: PipelineState) -> PipelineState:
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

def end_node(state: PipelineState) -> PipelineState:
    logger.debug("✅ [End] state finale: %s", state)
    out: PipelineState = {}
    for key in ("domain", "problem", "validation", "error_message", "refined_domain", "refined_problem"):
        if key in state:
            out[key] = state[key]
    return out

# ============================
# 🔄 Controllo branching
# ============================
from langchain_core.messages import HumanMessage

def should_continue_after_refine(state: PipelineState) -> dict[str, Any]:
    user_msgs = [m for m in state.get("messages", []) if isinstance(m, HumanMessage)]

    # Se non ci sono messaggi umani (prima interazione dopo refine)
    if not user_msgs:
        msg = input("💬 Inserisci feedback umano ('ok' per terminare): ").strip()
        new_msg = HumanMessage(content=msg)
        state["messages"].append(new_msg)

        if msg.lower() in {"ok", "accetta", "va bene"}:
            return {"next": "End", "state": state}
        return {"next": "Refine", "state": state}

    # Se esiste già un messaggio, valuta l’ultimo
    last = user_msgs[-1].content.strip().lower()
    if last in {"ok", "accetta", "va bene", "accetto"}:
        return {"next": "End", "state": state}

    return {"next": "Refine", "state": state}







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
    builder.add_node("ChatFeedback", node_chat_feedback)
    builder.add_node("End", end_node)

    # Flusso base
    builder.set_entry_point("BuildPrompt")
    builder.add_edge("BuildPrompt", "Generate")
    builder.add_edge("Generate", "Validate")
    builder.add_edge("Validate", "Refine")
    builder.add_edge("Refine", "ChatFeedback")

    # Rami condizionali da ChatFeedback
    builder.add_edge("ChatFeedback", "Refine")  # richiesto da LangGraph anche se condizionale
    builder.add_edge("ChatFeedback", "End")     # richiesto da LangGraph anche se condizionale
    builder.add_conditional_edges("ChatFeedback", path=should_continue_after_refine)

    # Compilazione finale
    return builder.compile(checkpointer=checkpointer) if checkpointer else builder.compile()





from langgraph.checkpoint.sqlite import SqliteSaver

def get_pipeline_with_memory(thread_id: str):
    logger.info(f"🧠 Pipeline persistente per thread: {thread_id}")
    logger.info(f"📍 Salvataggio in: memory/{thread_id}.sqlite")

    os.makedirs("memory", exist_ok=True)

    # ✅ Usa l'istanza direttamente, SENZA context manager
    saver = SqliteSaver.from_conn_string(f"sqlite:///memory/{thread_id}.sqlite")

    # ✅ Passalo dentro build_pipeline
    pipeline = build_pipeline(checkpointer=saver)

    # ✅ Aggiungi configurazione
    return pipeline.with_config(configurable={"thread_id": thread_id})







__all__ = ["get_pipeline_with_memory"]