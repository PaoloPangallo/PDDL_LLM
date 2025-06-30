from flask import Blueprint, request, jsonify
from pddl_pipeline import graph
import json
import os
from datetime import datetime
import traceback  # ✅
from db.db import save_generation_session


pipeline_bp = Blueprint("pipeline", __name__)

@pipeline_bp.route("/api/pipeline/run", methods=["POST"])
def run_pipeline():
    try:
        lore = request.get_json(force=True)
        if not lore:
            return jsonify({"error": "Lore JSON mancante o vuoto."}), 400

        print("📥 JSON ricevuto correttamente.")

        result = graph.invoke({"lore": lore})
        print("✅ Pipeline completata. Risultato:", result)

        session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        output_dir = os.path.join("uploads", session_id)
        os.makedirs(output_dir, exist_ok=True)

        def save(text, filename):
            with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
                f.write(text.strip() if text else "")

        save(result.get("domain"), "domain.pddl")
        save(result.get("problem"), "problem.pddl")
        save(json.dumps(result.get("validation"), indent=2, ensure_ascii=False), "validation.json")

        if result.get("refined_domain"):
            save(result.get("refined_domain"), "domain_refined.pddl")
        if result.get("refined_problem"):
            save(result.get("refined_problem"), "problem_refined.pddl")

        # ✅ Salvataggio nel database
        save_generation_session({
            "session_id": session_id,
            "lore": json.dumps(lore, indent=2, ensure_ascii=False),
            "domain": result.get("domain"),
            "problem": result.get("problem"),
            "validation": json.dumps(result.get("validation"), indent=2, ensure_ascii=False),
            "refined_domain": result.get("refined_domain"),
            "refined_problem": result.get("refined_problem"),
        })

        # ✅ Risposta HTTP
        return jsonify({
            "session_id": session_id,
            "domain": result.get("domain"),
            "problem": result.get("problem"),
            "validation": result.get("validation"),
            "refined": bool(result.get("refined_domain")),
        })

    except Exception as e:
        print("❌ Errore nella pipeline:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500