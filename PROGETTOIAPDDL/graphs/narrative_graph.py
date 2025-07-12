import os
import csv
import json
import logging
import sqlite3
from typing import TypedDict, Annotated, Any, Dict, List, Optional

from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import BaseMessage

from agents.narrative_agent import NarrativeAgent
from core.utils import save_lore

logger = logging.getLogger("narrative_pipeline")
logger.setLevel(logging.DEBUG)

# ============================
# 🧠 Stato della pipeline
# ============================

def last(_, right: Any) -> Any:
    return right

class NarrativeState(TypedDict):
    thread_id: str
    lore: Dict[str, Any]
    plan_steps: List[Dict[str, Any]]
    current_step: Annotated[int, last]
    enriched_plan: List[Dict[str, Any]]
    latest_step: Dict[str, Any]
    latest_lore_update: Dict[str, Any]

    chat_feedback: Annotated[Optional[str], last]
    chat_response: Annotated[Dict[str, Any], last]
    messages: Annotated[List[BaseMessage], last]


# ============================
# 🔁 Nodi LangGraph
# ============================

def node_load_plan(state: NarrativeState) -> NarrativeState:
    plan_path = os.path.join("uploads", "plan.csv")
    try:
        with open(plan_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            steps = [row for row in reader if row.get("action")]
        logger.info("✅ Piano caricato: %d step", len(steps))
    except Exception as e:
        logger.error("❌ Impossibile caricare il piano da %s: %s", plan_path, e, exc_info=True)
        steps = []

    return {
        **state,
        "plan_steps": steps,
        "current_step": 0,
        "enriched_plan": []
    }

def node_narrate_step(state: NarrativeState):
    agent = NarrativeAgent()
    lore = state.get("lore", {})
    steps = state.get("plan_steps", [])
    i = state.get("current_step", 0)

    if i >= len(steps):
        logger.debug("All steps processed, skipping narrate_step.")
        yield state
        return

    step_data = steps[i]
    action = step_data.get("action", "").strip()
    logger.info("🧠 Arricchimento step %d: %s", i, action)

    result = agent.ask_about_step(action, lore)

    narration = result.get("narration", f"Nessuna narrazione per '{action}'")
    question = result.get("follow_up_question", "Vuoi proseguire?")
    lore_update = result.get("lore_update", {})

    step_out = {
        "step": step_data.get("step", str(i)),
        "action": action,
        "narration": narration,
        "question": question,
        "lore_update": lore_update
    }

    yield {"event": "step", "data": step_out["step"]}
    yield {"event": "narration", "data": narration}
    yield {"event": "question", "data": question}

    yield {
        **state,
        "latest_step": step_out,
        "latest_lore_update": lore_update
    }

def node_chat_feedback(state: NarrativeState) -> NarrativeState:
    user_msg = state.get("chat_feedback", "").strip()
    if not user_msg:
        logger.debug("🖊️ Nessun feedback utente, passo oltre.")
        return state

    agent = NarrativeAgent()
    try:
        result = agent.respond_to_feedback(user_msg, state)
        logger.info("✅ Feedback umano processato dal modello.")
    except Exception as e:
        logger.error("Errore durante risposta al feedback: %s", e, exc_info=True)
        result = {}

    return {
        **state,
        "chat_response": result,
        "latest_step": result.get("latest_step", state.get("latest_step")),
        "latest_lore_update": result.get("lore_update", state.get("latest_lore_update", {}))
    }

def node_apply_lore_update(state: NarrativeState) -> NarrativeState:
    agent = NarrativeAgent()
    original = state.get("lore", {})
    updates = state.get("latest_lore_update", {})
    try:
        lore_updated = agent.update_lore(original, updates)
        logger.debug("Lore aggiornata con %d chiavi.", len(updates))
    except Exception as e:
        logger.error("Errore during lore update: %s", e, exc_info=True)
        lore_updated = original
    return {**state, "lore": lore_updated}

def node_append_to_plan(state: NarrativeState):
    enriched = state.get("enriched_plan", [])
    latest = state.get("latest_step")
    if latest:
        enriched = enriched + [latest]
        logger.debug("Step appended to enriched_plan: %s", latest)
        yield {"event": "append", "data": latest.get("action", "")}
    else:
        logger.warning("⚠️ latest_step mancante, non appendo nulla.")
    yield {**state, "enriched_plan": enriched}

def node_next_step(state: NarrativeState) -> NarrativeState:
    next_idx = state.get("current_step", 0) + 1
    logger.debug("NextStep: incrementing current_step to %d", next_idx)
    return {**state, "current_step": next_idx}

def is_finished(state: NarrativeState) -> bool:
    finished = state.get("current_step", 0) >= len(state.get("plan_steps", []))
    logger.debug("is_finished? %s", finished)
    return finished

def should_apply_feedback(state: NarrativeState) -> bool:
    return bool(state.get("chat_feedback"))

def end_node(state: NarrativeState):
    try:
        save_lore("uploads/lore_updated.json", state.get("lore", {}))
        with open("uploads/enriched_plan.json", "w", encoding="utf-8") as f:
            json.dump(state.get("enriched_plan", []), f, indent=2, ensure_ascii=False)
        logger.info("✅ Piano arricchito e lore salvati.")
        yield {"event": "done", "data": "✅ Avventura completata."}
    except Exception as e:
        logger.error("Errore saving outputs: %s", e, exc_info=True)
        yield {"event": "error", "data": str(e)}
    yield state

# ============================
# ⚙️ Costruzione del grafo
# ============================

def build_narrative_pipeline(checkpointer=None):
    builder = StateGraph(NarrativeState, stateful=True)

    builder.add_node("LoadPlan", node_load_plan)
    builder.add_node("NarrateStep", node_narrate_step)
    builder.add_node("ChatFeedback", node_chat_feedback)
    builder.add_node("ApplyLoreUpdate", node_apply_lore_update)
    builder.add_node("AppendToPlan", node_append_to_plan)
    builder.add_node("NextStep", node_next_step)
    builder.add_node("End", end_node)

    builder.set_entry_point("LoadPlan")
    builder.add_edge("LoadPlan", "NarrateStep")
    builder.add_edge("NarrateStep", "ChatFeedback")
    builder.add_conditional_edges("ChatFeedback", should_apply_feedback, {
        True: "ApplyLoreUpdate",
        False: "AppendToPlan"
    })
    builder.add_edge("ApplyLoreUpdate", "AppendToPlan")
    builder.add_edge("AppendToPlan", "NextStep")
    builder.add_conditional_edges("NextStep", is_finished, {
        True: "End",
        False: "NarrateStep"
    })

    return builder.compile(checkpointer=checkpointer)

# ============================
# 🚀 Inizializzazione
# ============================

def get_pipeline_with_memory(thread_id: str, reset: bool = True):
    logger.info("🧠 [Narrative] Pipeline persistente per thread: %s", thread_id)

    db_dir = os.path.abspath("memory")
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, f"narrative_{thread_id}.sqlite")

    if reset and os.path.exists(db_path):
        os.remove(db_path)
        logger.warning("🧹 Memoria narrative reset: %s", db_path)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    saver = SqliteSaver(conn)

    if reset:
        try:
            with conn:
                conn.execute("DROP TABLE IF EXISTS state")
                conn.execute("DROP TABLE IF EXISTS checkpoints")
            logger.debug("Tabelle narrative SQLite rimosse")
        except Exception as e:
            logger.error("Errore durante reset DB narrative: %s", e, exc_info=True)

    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='checkpoints'")
        if cur.fetchone()[0]:
            cur.execute("SELECT COUNT(*) FROM checkpoints")
            logger.info("📂 Checkpoints esistenti: %d", cur.fetchone()[0])
        else:
            logger.info("📫 Nessuna tabella checkpoint narrativa presente.")
    except Exception as e:
        logger.warning("Errore diagnostica DB narrative: %s", e, exc_info=True)

    graph = build_narrative_pipeline(checkpointer=saver)
    return graph.with_config(configurable={"thread_id": thread_id})
