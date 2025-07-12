"""
PDDL pipeline graph: genera, valida e raffina file PDDL con persistenza su SQLite.
"""

import os
import json
import logging
import re
import shutil
import sqlite3
from typing import Any, TypedDict, Optional, Dict, List, Annotated, cast

from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from core.generator import build_prompt_from_lore
from db.db import retrieve_similar_examples_from_db
from core.utils import ask_ollama, extract_between, save_text_file
from core.validator import validate_pddl, generate_plan_with_fd
from agents.reflection_agent import refine_pddl

# ---------------------
# Logging
# ---------------------
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("pddl_pipeline_graph")

# -------------------------------------------------
# Gestione dello stato - Politiche di merging
# -------------------------------------------------
def last(_old, new): 
    return new

def non_empty_or_last(old, new):
    """
    Se `new` è None o stringa vuota, ritorna `old`, 
    altrimenti ritorna `new`.
    """
    if new is None:
        return old
    if isinstance(new, str) and new.strip() == "":
        return old
    return new

# ---------------------
# Stato della pipeline
# ---------------------
class PipelineState(TypedDict):
    lore: Annotated[Dict[str, Any], last]
    thread_id: Annotated[str, last]

    tmp_dir: Annotated[Optional[str], last]
    prompt: Annotated[Optional[str], last]

    # Qui applico non_empty_or_last
    domain: Annotated[Optional[str], non_empty_or_last]
    problem: Annotated[Optional[str], non_empty_or_last]
    refined_domain: Annotated[Optional[str], non_empty_or_last]
    refined_problem: Annotated[Optional[str], non_empty_or_last]

    validation: Annotated[Optional[dict], last]
    error_message: Annotated[Optional[str], last]
    status: Annotated[Optional[str], last]

    attempt: Annotated[int, last] #viene incrementato manualmente ad ogni refine
    messages: Annotated[List[BaseMessage], last]

    plan: Annotated[Optional[str], last]
    plan_log: Annotated[Optional[str], last]


# ---------------------
# Parametri globali
# ---------------------
MAX_REFINE_ATTEMPTS = 3

# ---------------------
# Helpers
# ---------------------
def is_positive_feedback(msg: str) -> bool:
    return msg.strip().lower() in {
        "ok", "va bene", "accetto", "accetta",
        "perfetto", "tutto ok", "confermato"
    }

# ---------------------
# Nodi
# ---------------------
def node_build_prompt(state: PipelineState) -> PipelineState:
    print("\n=== Enter node_build_prompt ===")
    print(f"Stato in ingresso: attempt={state.get('attempt')}, status={state.get('status')}")
    thread_id = state["thread_id"]
    upload_dir = os.path.join("static", "uploads", thread_id)
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir)
    os.makedirs(upload_dir, exist_ok=True)

    examples = [
        str(e)
        for e in retrieve_similar_examples_from_db(state["lore"], k=1)
        if isinstance(e, str)
    ]
    prompt, _ = build_prompt_from_lore(state["lore"], examples=examples)

    new_state = {**state,
        "tmp_dir": upload_dir,
        "prompt": prompt,
        "status": "ok",
        "attempt": 0
    }
    print(f"Prompt generato, tmp_dir={upload_dir}")
    print("=== Exit node_build_prompt ===\n")
    return cast(PipelineState, new_state)

def node_generate_pddl(state: PipelineState) -> PipelineState:
    print("\n=== Enter node_generate_pddl ===")
    print(f"Stato in ingresso: status={state.get('status')}")
    if state.get("status") != "ok":
        print("Skip generate: status != ok")
        return cast(PipelineState, {**state, "status": "failed", "error_message": "Skipped generate"})

    try:
        print("Invio prompt a LLM...")
        response = ask_ollama(state["prompt"] or "")
        tmp = state["tmp_dir"] or ""
        save_text_file(os.path.join(tmp, "raw_response.txt"), response)

        dom_raw = extract_between(response, "=== DOMAIN START ===", "=== DOMAIN END ===")
        prob_raw = extract_between(response, "=== PROBLEM START ===", "=== PROBLEM END ===")
        if not dom_raw or not prob_raw:
            raise ValueError("Formato PDDL non trovato")

        clean = lambda t: re.sub(r"```(?:\w*\n)?(.*?)```", r"\1", t, flags=re.DOTALL)
        domain  = clean(dom_raw)
        problem = clean(prob_raw)

        save_text_file(os.path.join(tmp, "domain.pddl"), domain)
        save_text_file(os.path.join(tmp, "problem.pddl"), problem)

        print("Domain e Problem salvati su disco.")
        print("=== Exit node_generate_pddl ===\n")
        return cast(PipelineState, {**state,
            "domain": domain,
            "problem": problem,
            "status": "ok",
            "error_message": None
        })
    except Exception as e:
        print(f"Errore in generate: {e}")
        logger.error("GeneratePDDL — %s", e, exc_info=True)
        return cast(PipelineState, {**state,
            "status": "failed",
            "error_message": f"Generate error: {e}"
        })

def node_validate(state: PipelineState) -> PipelineState:
    print("\n=== Enter node_validate ===")
    print(f"Stato in ingresso: status={state.get('status')}, attempt={state.get('attempt')}")
    if state.get("status") != "ok":
        print("Skip validate: status != ok")
        return cast(PipelineState, {**state, "status": "failed", "error_message": "Skipped validate"})

    domain = state.get("refined_domain") or state.get("domain") or ""
    problem = state.get("refined_problem") or state.get("problem") or ""

    print("Avvio validate_pddl()...")
    validation = validate_pddl(domain, problem, state["lore"])
    valid = validation.get("valid_syntax", False)
    sem_err = validation.get("semantic_errors", [])

    if valid and not sem_err:
        print("Validate → OK")
        print("=== Exit node_validate ===\n")
        return cast(PipelineState, {**state,
            "validation": validation,
            "status": "ok",
            "error_message": None
        })
    else:
        print("Validate → FAILED")
        print("Errors:", validation)
        print("=== Exit node_validate ===\n")
        return cast(PipelineState, {**state,
            "validation": validation,
            "status": "failed",
            "error_message": "Validation errors"
        })

def node_refine(state: PipelineState) -> PipelineState:
    print("\n=== Enter node_refine ===")
    print(f"Stato in ingresso: status={state.get('status')}, attempt={state.get('attempt')}")
    if state.get("status") != "failed":
        print("Skip refine: status != failed")
        print("=== Exit node_refine ===\n")
        return state

    tmp = state.get("tmp_dir") or ""
    try:
        print("Chiamata a refine_pddl()...")
        updated = refine_pddl(
            domain_path=os.path.join(tmp, "domain.pddl"),
            problem_path=os.path.join(tmp, "problem.pddl"),
            error_message=state.get("error_message") or "",
            lore=state["lore"]
        )
        rd = extract_between(updated, "=== DOMAIN START ===", "=== DOMAIN END ===") or ""
        rp = extract_between(updated, "=== PROBLEM START ===", "=== PROBLEM END ===") or ""
        save_text_file(os.path.join(tmp, "domain_refined.pddl"), rd)
        save_text_file(os.path.join(tmp, "problem_refined.pddl"), rp)

        new_attempt = state.get("attempt", 0) + 1
        print(f"Refine completato → nuovo attempt = {new_attempt}")
        print("=== Exit node_refine ===\n")
        return cast(PipelineState, {**state,
            "refined_domain": rd,
            "refined_problem": rp,
            "domain": rd,
            "problem": rp,
            "error_message": None,
            "attempt": new_attempt,
            "status": "ok"
        })
    except Exception as e:
        print(f"Errore in refine: {e}")
        logger.error("Refine — %s", e, exc_info=True)
        return cast(PipelineState, {**state,
            "status": "failed",
            "error_message": str(e)
        })

def node_chat_feedback(state: PipelineState) -> PipelineState:
    msgs = state.get("messages", [])
    # 1) nessun nuovo messaggio → pausa
    if not msgs:
        return { **state, "status": "awaiting_feedback" }

    last_msg = msgs[-1]
    content = last_msg.content
    if isinstance(last_msg, HumanMessage) and isinstance(content, str) and is_positive_feedback(content):
        # 2) feedback positivo → fine
        return { **state, "status": "ok" }

    # 3) feedback umano negativo → rigenera via LLM
    # Ensure content is a string for feedback
    if isinstance(content, str):
        feedback_str = content.strip()
    elif isinstance(content, list):
        # Join list elements as string, handling dicts if present
        feedback_str = " ".join(
            [str(item) if not isinstance(item, dict) else json.dumps(item) for item in content]
        ).strip()
    else:
        feedback_str = str(content).strip()

    prompt = (
        "You are a PDDL refinement assistant.\n"
        f"Human feedback: \"{feedback_str}\"\n\n"
        "=== DOMAIN START ===\n"  + (state.get("domain") or "") + "\n=== DOMAIN END ===\n\n"
        "=== PROBLEM START ===\n" + (state.get("problem") or "") + "\n=== PROBLEM END ===\n\n"
        "Validation Summary:\n" + json.dumps(state.get("validation") or {}, indent=2) +
        "\n\nPlease rewrite both files fixing the issues."
    )
    resp = ask_ollama(prompt)
    rd = extract_between(resp, "=== DOMAIN START ===",   "=== DOMAIN END ===")   or ""
    rp = extract_between(resp, "=== PROBLEM START ===",  "=== PROBLEM END ===")  or ""
    tmp = state["tmp_dir"] or ""
    save_text_file(os.path.join(tmp,"domain_refined.pddl"), rd)
    save_text_file(os.path.join(tmp,"problem_refined.pddl"), rp)

    return {
        **state,
        "domain": rd,
        "problem": rp,
        "refined_domain": rd,
        "refined_problem": rp,
        "status": "ok",
        "messages": [AIMessage(content=resp)] #registro anche la risposta dell’agente in memoria
    }


def feedback_branch(state: PipelineState) -> Optional[str]:
    # se ancora in attesa, resto qui (None = nessun ramo, pause)
    if state.get("status") == "awaiting_feedback":
        return None
    # se OK, fine
    if state.get("status") == "ok":
        return "End"
    # altrimenti rientro in refine
    return "Refine"


def end_node(state: PipelineState) -> PipelineState:
    print("\n=== Enter end_node ===")
    print(f"Stato finale: attempt={state.get('attempt')}, status={state.get('status')}")
    print("=== Exit end_node ===\n")
    return state

# ---------------------
# Branching logic
# ---------------------
def validate_decision(state: PipelineState) -> str:
    print("\n>>> validate_decision <<<")
    em = state.get("error_message")
    attempt = state.get("attempt", 0)
    print(f"error_message={em}, attempt={attempt}/{MAX_REFINE_ATTEMPTS}")
    if not em:
        print("→ nessun errore → GeneratePlan")
        return "GeneratePlan"
    if attempt <= MAX_REFINE_ATTEMPTS:
        state["attempt"] = attempt + 1
        print(f"→ errore ma attempt < MAX → Refine (ora attempt={state['attempt']})")
        return "Refine"
    print("→ attempt >= MAX → ChatFeedback")
    return "ChatFeedback"

def node_generate_plan(state: PipelineState) -> PipelineState:
    """
    Runs Fast-Downward on the (refined) domain/problem and
    attaches the plan and log back into state.
    """
    print("\n=== Enter GeneratePlan_node ===")
    dom = state.get("refined_domain") or state.get("domain") or ""
    prob = state.get("refined_problem") or state.get("problem") or ""

    # guard in case something is missing
    if not dom or not prob:
        return { **state,
                 "status": "failed",
                 "error_message": "Missing domain or problem for planning" }

    # call your Fast-Downward wrapper
    result = generate_plan_with_fd(dom, prob)
    if result.get("found_plan"):
        print(f"\n{result["plan"]}\n")
        print("=== Exit GeneratePlan_node ===\n")
        return {
            **state,
            "plan":     result["plan"],
            "plan_log": result["log"],
            "status":   "ok",
            "error_message": None
        }
    else:
        print("Nessun piano trovato...")
        print("=== Exit GeneratePlan_node ===\n")
        return {
            **state,
            "plan":     None,
            "plan_log": result["log"],
            "status":   "failed",
            "error_message": "Planning failed"
        }
# ---------------------
# Costruzione del grafo
# ---------------------
def build_pipeline(checkpointer=None):
    builder = StateGraph(PipelineState)

    # (ri)definisci tutti i nodi che già avevi: BuildPrompt, Generate, Validate, Refine…
    builder.add_node("BuildPrompt",   node_build_prompt)
    builder.add_node("Generate",      node_generate_pddl)
    builder.add_node("Validate",      node_validate)
    builder.add_node("Refine",        node_refine)
    builder.add_node("ChatFeedback",  node_chat_feedback)
    builder.add_node("GeneratePlan",  node_generate_plan)
    builder.add_node("End",           end_node)

    # flusso base
    builder.set_entry_point("BuildPrompt")
    builder.add_edge("BuildPrompt", "Generate")
    builder.add_edge("Generate",    "Validate")

    # Validate → { Refine | End | ChatFeedback }
    builder.add_conditional_edges("Validate", path=validate_decision)

    # quando refini, torni a validare
    builder.add_edge("Refine", "Validate")

    # ChatFeedback → { Refine | End }, ma in pausa finché feedback_branch non sblocca
    builder.add_conditional_edges("ChatFeedback", path=feedback_branch)

    # Dopo aver generato il piano → End
    builder.add_edge("GeneratePlan", "End")

    return builder.compile(checkpointer=checkpointer)

# ---------------------
# Pipeline con memoria
# ---------------------

def get_pipeline_with_memory(thread_id: str, reset: bool=False):
    db = f"memory/{thread_id}.sqlite"
    os.makedirs(os.path.dirname(db), exist_ok=True)
    if reset and os.path.exists(db):
        os.remove(db)
    conn = sqlite3.connect(db, check_same_thread=False)
    saver = SqliteSaver(conn)
    return build_pipeline(checkpointer=saver).with_config(configurable={"thread_id":thread_id})


# def get_pipeline_with_memory(thread_id: str, reset: bool = False):
#     print(f"\n>>> get_pipeline_with_memory(thread_id={thread_id}, reset={reset})")
#     db = os.path.abspath(f"memory/{thread_id}.sqlite")
#     os.makedirs(os.path.dirname(db), exist_ok=True)
#     if reset and os.path.exists(db):
#         os.remove(db)

#     conn = sqlite3.connect(db, check_same_thread=False)
#     saver = SqliteSaver(conn)
#     if reset:
#         with conn:
#             conn.execute("DROP TABLE IF EXISTS state")
#             conn.execute("DROP TABLE IF EXISTS checkpoints")

#     pipeline = build_pipeline(checkpointer=saver)
#     pipeline = pipeline.with_config(configurable={"thread_id": thread_id})
#     print("Pipeline with memory creata\n")
#     return pipeline


