import os

# Lista delle directory da creare
directories = [
    "agents",
    "core",
    "graphs",
    "routes",
    "static/js",
    "static/css",
    "templates",
    "uploads"
]

# File da creare con contenuto opzionale iniziale
files_to_create = {
    "agents/narrative_agent.py": "# LLM agent per arricchimento narrativo del piano\n",
    "core/narrative.py": "# Parser e arricchitore del piano\n",
    "graphs/narrative_graph.py": "# LangGraph per conversazione narrativa\n",
    "routes/narrative_route.py": "# Endpoint Flask per esperienza narrativa\n",
    "static/js/narrative.js": "// JS interattivo per frontend narrativo\n",
    "static/css/narrative.css": "/* Stile per l'interfaccia narrativa */\n",
    "templates/narrative.html": "<!-- HTML per la storia interattiva -->\n",
    "uploads/enriched_plan.json": "[]\n"  # JSON iniziale vuoto
}

def setup_phase2():
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"📁 Directory creata o esistente: {directory}")

    for filepath, content in files_to_create.items():
        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"📝 File creato: {filepath}")
        else:
            print(f"⚠️ File già esistente: {filepath}")

if __name__ == "__main__":
    setup_phase2()
