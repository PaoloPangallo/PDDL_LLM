from graphs.pddl_pipeline_graph import get_pipeline_with_memory
import json

if __name__ == "__main__":
    with open("lore/example_lore.json", encoding="utf-8") as f:
        lore_data = json.load(f)

    pipeline = get_pipeline_with_memory("session-1")

    result = pipeline.invoke({
        "lore": lore_data,
        "tmp_dir": "",
        "prompt": None,
        "status": "ok"
    })

    print("=== Risultato finale ===\n", json.dumps(result, indent=2, ensure_ascii=False))
