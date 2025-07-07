import json
from langchain_core.messages import HumanMessage
from graphs.pddl_pipeline_graph import get_pipeline_with_memory

def run_pipeline(session_id: str = "session-1"):
    # Carica lore
    with open("lore/example_lore.json", encoding="utf-8") as f:
        lore_data = json.load(f)

    pipeline = get_pipeline_with_memory(session_id)

    # Stato iniziale
    state = {
        "lore": lore_data,
        "status": "ok",
        "messages": []  # 🧠 Serve per supportare feedback umano
    }

    # 1️⃣ Esegui pipeline
    result = pipeline.invoke(state)

    print("=== 🧾 Risultato ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 2️⃣ Se fallisce, chiedi feedback umano
    if result.get("status") == "failed":
        print("\n⚠️ La pipeline ha fallito. Vuoi fornire un feedback manuale? (s/n)")
        choice = input("> ").lower().strip()
        if choice == "s":
            feedback = input("\n💬 Inserisci il tuo messaggio di feedback:\n> ")
            state["messages"].append(HumanMessage(content=feedback))

            # Rilancia il nodo `ChatFeedback` manualmente
            result = pipeline.invoke(state, config={"node": "ChatFeedback"})

            print("\n=== 🔁 Risultato dopo ChatFeedback ===")
            print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    run_pipeline()
