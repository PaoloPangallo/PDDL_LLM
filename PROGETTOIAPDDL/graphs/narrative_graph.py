import os
import csv
import json
import logging
import sqlite3
from typing import TypedDict, Annotated, Any, Dict, List, Optional


from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt

from agents.narrative_agent import NarrativeAgent
from core.utils import save_lore

logger = logging.getLogger("narrative_pipeline")
logger.setLevel(logging.INFO)


# ===========================
# 🧠 Stato della pipeline
# ===========================

def last(_, right: Any) -> Any:
    return right


class NarrativeState(TypedDict):
    thread_id: str
    lore: Dict[str, Any]
    plan_steps: List[Dict[str, Any]]
    current_step: Annotated[int, last]

    latest_step: Dict[str, Any]
    latest_lore_update: Dict[str, Any]

    chat_feedback: Annotated[Optional[str], last]
    chat_response: Annotated[Dict[str, Any], last]


# ===========================
# 🔁 Nodi
# ===========================

def node_load_plan(state: NarrativeState):
    plan_path = os.path.join("uploads", "plan.csv")
    try:
        with open(plan_path, encoding="utf-8") as f:

            reader = csv.DictReader(f)
            steps = [row for row in reader if row.get("action")]
        logger.info("✅ Piano caricato: %d step", len(steps))
    except Exception as e:
        logger.error("❌ Errore nel caricamento piano: %s", e, exc_info=True)
        steps = []

    return {
        **state,
        "plan_steps": steps,
        "current_step": 0,
        "latest_step": {},
        "latest_lore_update": {},
        "chat_feedback": None,
        "chat_response": {},
    }


def node_emit_plan(state: NarrativeState):
    yield {
        "LoadPlan": {
            "plan_steps": state.get("plan_steps", []),
            "lore": state.get("lore", {}),
        }
    }
    return state


from langgraph.types import interrupt

def node_narrate_step(state: NarrativeState):
    agent = NarrativeAgent()
    lore = state.get("lore", {})
    steps = state.get("plan_steps", [])
    i = state.get("current_step", 0)

    if i >= len(steps):
        logger.info("🏁 Fine narrazione: tutti gli step completati.")
        return state

    step_data = steps[i]
    action = step_data.get("action", "").strip()
    logger.info("🎙️ Narro step %d: %s", i, action)

    try:
        res = agent.ask_about_step(action, lore) or {}
    except Exception as e:
        logger.error("❌ ask_about_step: %s", e, exc_info=True)
        res = {}

    narration   = res.get("narration", f"Nessuna narrazione per «{action}»")
    question    = res.get("follow_up_question", "Vuoi proseguire?")
    lore_update = res.get("lore_update", {})

    step_out = {
        "step": step_data.get("step", str(i)),
        "action": action,
        "narration": narration,
        "question": question,
        "lore_update": lore_update,
    }

    # Eventi opzionali tecnici (possono anche essere rimossi se usi solo interrupt)
    yield {"NarrateStep": {"step": step_out["step"]}}
    yield {"Narration": {"narration": narration}}
    yield {"Question": {"question": question}}

    # 👉 Interrompi per mostrare nel frontend la narrazione + domanda + form feedback
    return interrupt({
        "value": "💬 Invia un feedback utente:",
        "narration": narration,
        "question": question,
        "step": step_out,
        "resumable": True,
        "namespace": f"AskFeedback:{state.get('thread_id', 'default')}"
    })



def node_ask_feedback(state: NarrativeState):
    yield {"ChatFeedback": {"thread_id": state["thread_id"]}}
    # 👇 Pausa: attende un input utente su 'chat_feedback'
    feedback = interrupt("💬 Invia un feedback utente:")
    return {"chat_feedback": feedback}


def node_handle_feedback(state: NarrativeState):
    msg = state.get("chat_feedback", "").strip()
    agent = NarrativeAgent()
    try:
        result = agent.respond_to_feedback(msg, state) or {}
        logger.info("✅ Feedback processato.")
    except Exception as e:
        logger.error("❌ respond_to_feedback: %s", e, exc_info=True)
        result = {}

    return {
        **state,
        "chat_response": result,
        "latest_step": result.get("latest_step", state.get("latest_step")),
        "latest_lore_update": result.get("lore_update", state.get("latest_lore_update", {})),
        "chat_feedback": None
    }


def node_apply_lore_update(state: NarrativeState):
    agent = NarrativeAgent()
    try:
        updated = agent.update_lore(state.get("lore", {}), state.get("latest_lore_update", {}))
    except Exception:
        updated = state.get("lore", {})
    return {**state, "lore": updated}


def node_append_to_plan(state: NarrativeState):
    latest = state.get("latest_step")
    if latest:
        yield {"AppendToPlan": {"action": latest.get("action", "")}}
    return state


def node_next_step(state: NarrativeState):
    return {**state, "current_step": state.get("current_step", 0) + 1}


def is_finished(state: NarrativeState):
    return state.get("current_step", 0) >= len(state.get("plan_steps", []))


def end_node(state: NarrativeState):
    save_lore("uploads/lore_updated.json", state.get("lore", {}))
    with open("uploads/enriched_plan.json", "w", encoding="utf-8") as f:
        json.dump(state.get("plan_steps", []), f, indent=2, ensure_ascii=False)
    return {"Done": {"message": "✅ Avventura completata."}}


# ===========================
# ⚙️ Costruzione Grafo
# ===========================

def build_narrative_pipeline(checkpointer=None):
    g = StateGraph(NarrativeState, stateful=True)

    g.add_node("LoadPlan", node_load_plan)
    g.add_node("EmitPlan", node_emit_plan)
    g.add_node("NarrateStep", node_narrate_step)
    g.add_node("AskFeedback", node_ask_feedback)
    g.add_node("HandleFeedback", node_handle_feedback)
    g.add_node("ApplyLoreUpdate", node_apply_lore_update)
    g.add_node("AppendToPlan", node_append_to_plan)
    g.add_node("NextStep", node_next_step)
    g.add_node("End", end_node)

    g.set_entry_point("LoadPlan")

    g.add_edge("LoadPlan", "EmitPlan")
    g.add_edge("EmitPlan", "NarrateStep")
    g.add_edge("NarrateStep", "AskFeedback")
    g.add_edge("AskFeedback", "HandleFeedback")
    g.add_edge("HandleFeedback", "ApplyLoreUpdate")
    g.add_edge("ApplyLoreUpdate", "AppendToPlan")
    g.add_edge("AppendToPlan", "NextStep")
    g.add_conditional_edges("NextStep", is_finished, {True: "End", False: "NarrateStep"})

    return g.compile(checkpointer=checkpointer)


# ===========================
# 🚀 Avvio con memoria SQLite
# ===========================

def get_pipeline_with_memory(thread_id: str, reset: bool = True):
    logger.info("🧠 Pipeline thread: %s", thread_id)
    db_dir = os.path.abspath("memory")
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, f"narrative_{thread_id}.sqlite")

    if reset and os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    saver = SqliteSaver(conn)

    if reset:
        with conn:
            conn.execute("DROP TABLE IF EXISTS state")
            conn.execute("DROP TABLE IF EXISTS checkpoints")

    graph = build_narrative_pipeline(checkpointer=saver)
    return graph.with_config(configurable={"thread_id": thread_id})
