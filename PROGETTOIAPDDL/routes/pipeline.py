import os
import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from pddl_pipeline import graph
from db.db import save_generation_session

pipeline_bp = Blueprint("pipeline", __name__)
logger = logging.getLogger(__name__)

@pipeline_bp.route("/api/pipeline/run", methods=["POST"])
def run_pipeline():
    """
    Avvia la pipeline LangGraph per generare, validare e raffinare file PDDL da una lore.
    
    Richiede: JSON con campo 'lore' (dict con descrizione, oggetti, init).
    Restituisce: JSON con dominio, problema, validazione, raffinamento (se avvenuto) e session ID.
    """
    try:
        lore = request.get_json(force=True)
        if not lore:
            return jsonify({"error": "❌ Lore JSON mancante o vuoto."}), 400

        logger.info("📥 JSON ricevuto correttamente.")

        result = graph.invoke({"lore": lore})
        logger.info("✅ Pipeline completata.")

        session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        output_dir = os.path.join("uploads", session_id)
        os.makedirs(output_dir, exist_ok=True)

        def save(content: str | dict | None, filename: str) -> None:
            if content is None:
                return
            path = os.path.join(output_dir, filename)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content if isinstance(content, str) else json.dumps(content, indent=2, ensure_ascii=False))

        # Salva tutti gli output
        save(result.get("domain"), "domain.pddl")
        save(result.get("problem"), "problem.pddl")
        save(result.get("validation"), "validation.json")
        save(result.get("refined_domain"), "domain_refined.pddl")
        save(result.get("refined_problem"), "problem_refined.pddl")

        # Salva anche nel DB
        save_generation_session({
            "session_id": session_id,
            "lore": json.dumps(lore, indent=2, ensure_ascii=False),
            "domain": result.get("domain"),
            "problem": result.get("problem"),
            "validation": json.dumps(result.get("validation"), indent=2, ensure_ascii=False),
            "refined_domain": result.get("refined_domain"),
            "refined_problem": result.get("refined_problem"),
        })

        return jsonify({
            "session_id": session_id,
            "domain": result.get("domain"),
            "problem": result.get("problem"),
            "validation": result.get("validation"),
            "refined": bool(result.get("refined_domain")),
        })

    except Exception as err:
        logger.exception("❌ Errore durante l'esecuzione della pipeline.")
        return jsonify({"error": str(err)}), 500
