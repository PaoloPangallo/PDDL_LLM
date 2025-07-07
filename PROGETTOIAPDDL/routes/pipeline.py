import os
import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify

from pddl_pipeline import pipeline
from db.db import save_generation_session

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

pipeline_bp = Blueprint("pipeline", __name__)

@pipeline_bp.route("/api/pipeline/run", methods=["POST"])
def run_pipeline():
    """
    POST /api/pipeline/run
    {
      "lore": { ... }               # JSON lore inline
      oppure
      "lore_path": "example_lore.json"  # Nome file in /lore
    }
    """
    try:
        payload = request.get_json(force=True)
        if not payload:
            return jsonify({"error": "❌ Payload JSON mancante o vuoto."}), 400

        # 🧠 Caricamento lore da file o payload
        if "lore_path" in payload:
            lore_path = payload["lore_path"]

            # 📁 Path assoluto al file nella cartella /lore
            base_dir = os.path.abspath(os.path.dirname(__file__))
            full_path = os.path.join(base_dir, "..", "lore", lore_path)

            if not os.path.exists(full_path):
                logger.error("❌ File lore non trovato: %s", full_path)
                return jsonify({"error": f"❌ File lore non trovato: {lore_path}"}), 404

            try:
                with open(full_path, encoding="utf-8") as f:
                    lore = json.load(f)
                logger.info("📥 Lore caricata da file: %s", full_path)
            except Exception as e:
                logger.error("❌ Errore durante la lettura del file: %s", e)
                return jsonify({"error": f"❌ Impossibile leggere il file lore: {lore_path}"}), 400
        else:
            lore = payload.get("lore")
            if not isinstance(lore, dict):
                return jsonify({"error": "❌ Campo 'lore' mancante o non valido."}), 400

        # 🚀 Invoca la pipeline headless
        logger.info("🚀 Invoco pipeline PDDL...")
        result = pipeline.invoke({"lore": lore})
        logger.info("✅ Pipeline completata con successo.")

        # 📁 Salva su disco e su DB
        session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        output_dir = os.path.join("uploads", session_id)
        os.makedirs(output_dir, exist_ok=True)

        def _save(content, fname):
            if content is None:
                return
            path = os.path.join(output_dir, fname)
            with open(path, "w", encoding="utf-8") as f:
                if isinstance(content, str):
                    f.write(content)
                else:
                    json.dump(content, f, indent=2, ensure_ascii=False)

        _save(result.get("domain"),          "domain.pddl")
        _save(result.get("problem"),         "problem.pddl")
        _save(result.get("validation"),      "validation.json")
        _save(result.get("refined_domain"),  "domain_refined.pddl")
        _save(result.get("refined_problem"), "problem_refined.pddl")

        save_generation_session({
            "session_id":     session_id,
            "lore":           json.dumps(lore, indent=2, ensure_ascii=False),
            "domain":         result.get("domain"),
            "problem":        result.get("problem"),
            "validation":     json.dumps(result.get("validation", {}), indent=2, ensure_ascii=False),
            "refined_domain": result.get("refined_domain"),
            "refined_problem":result.get("refined_problem"),
        })

        return jsonify({
            "session_id": session_id,
            **result,
            "refined": bool(result.get("refined_domain"))
        })

    except Exception as err:
        logger.exception("❌ Errore durante l'esecuzione della pipeline.")
        return jsonify({"error": str(err)}), 500


@pipeline_bp.route("/api/lore_files", methods=["GET"])
def list_lore_files():
    """
    Ritorna i nomi dei file JSON disponibili in /lore (no path completo).
    """
    try:
        lore_dir = os.path.join(os.path.dirname(__file__), "..", "lore")
        files = [f for f in os.listdir(lore_dir) if f.endswith(".json")]
        files.sort()
        return jsonify(files)
    except Exception as e:
        logger.error("❌ Errore nella lettura della cartella lore/: %s", e)
        return jsonify({"error": "Impossibile caricare i file lore."}), 500
