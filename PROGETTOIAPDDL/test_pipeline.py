import os
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from graphs.pddl_pipeline_graph import build_pipeline

@contextmanager
def sqlite_saver_context(path: str):
    """
    Context manager che crea una connessione sqlite3 multi-thread-safe
    su file, costruisce un SqliteSaver e rilascia la connessione a fine blocco.
    """
    dirpath = os.path.dirname(path)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)

    # ✅ Permetti uso della connessione da più thread
    conn = sqlite3.connect(path, check_same_thread=False)

    saver = SqliteSaver(conn)
    try:
        yield saver
    finally:
        conn.close()



def run_pipeline(session_id: str = "session-1"):
    # Preparazione directory e percorso checkpoint
    ckpt_dir = "memory"
    os.makedirs(ckpt_dir, exist_ok=True)
    ckpt_path = os.path.join(ckpt_dir, f"{session_id}.sqlite")

    # Caricamento della lore
    with open("lore/example_lore.json", encoding="utf-8") as f:
        lore_data = json.load(f)

    with sqlite_saver_context(ckpt_path) as saver:
        pipeline = (
            build_pipeline(checkpointer=saver)
            .with_config(configurable={"thread_id": session_id})
        )

        # Recupero stato o inizializzo nuovo
        if os.path.exists(ckpt_path):
            print("♻️ Checkpoint già esistente. Continuo dal precedente stato.")
            state_snapshot = pipeline.get_state(config={"configurable": {"thread_id": session_id}})
            # Uso dataclasses.asdict per convertire in dict
            try:
                state = asdict(state_snapshot)
            except Exception:
                # Fallback a __dict__ se non dataclass
                state = getattr(state_snapshot, '__dict__', {})
            # Assicuro la presenza di lore
            state.setdefault('lore', lore_data)
        else:
            print("🚀 Nessun checkpoint trovato. Parto da zero.")
            state = {
                "lore": lore_data,
                "status": "ok",
                "messages": []
            }

        # Invocazione della pipeline
        result = pipeline.invoke(state)

        # Stampa del risultato
        print("=== 🧾 Risultato ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # Feedback in caso di failure
        if result.get("status") == "failed":
            print("\n⚠️ La pipeline ha fallito. Vuoi fornire un feedback manuale? (s/n)")
            if input("> ").strip().lower() == "s":
                fb = input("\n💬 Inserisci feedback:\n> ")
                messages = state.get('messages', [])
                messages.append(HumanMessage(content=fb))
                state['messages'] = messages

                result = pipeline.invoke(state, config={"node": "ChatFeedback"})
                print("\n=== 🔁 Risultato dopo ChatFeedback ===")
                print(json.dumps(result, indent=2, ensure_ascii=False))

        # Stampa stato finale compatto
        print("\n📦 Stato finale:")
        for k, v in result.items():
            if isinstance(v, str) and len(v) > 300:
                print(f"{k}: {v[:300]}... [troncato]")
            else:
                print(f"{k}: {v}")


if __name__ == "__main__":
    run_pipeline()
