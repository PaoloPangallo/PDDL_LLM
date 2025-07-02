"""
Modulo Flask per la visualizzazione del risultato della pianificazione PDDL.

Gestisce:
- visualizzazione del piano generato;
- parsing dei file di validazione;
- raffinamento automatico se il planner fallisce;
- visualizzazione cronologia chat e esempi RAG.
"""

import os
import json

from flask import Blueprint, request, render_template, current_app
from core.utils import read_text_file
from agents.reflection_agent import refine_and_save



result_bp = Blueprint("result", __name__)


@result_bp.route("/result")
def result():
    """
    Route per la visualizzazione della pagina dei risultati.
    Recupera file generati nella sessione, esegue raffinamento se necessario,
    e li passa al template result.html.
    """
    session = request.args.get("session")
    if not session:
        return "❌ Errore: ID di sessione mancante.", 400

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    session_dir = os.path.join(upload_folder, session)
    if not os.path.exists(session_dir):
        return f"❌ Errore: sessione {session} non trovata.", 404

    def safe_content(path, placeholder=""):
        """Legge il file e restituisce testo ripulito o un placeholder."""
        content = read_text_file(path)
        return content.strip() if content and content.strip() else placeholder

    paths = {
        "plan": os.path.join(session_dir, "plan.json"),
        "validation": os.path.join(session_dir, "validation.json"),
        "suggestion": os.path.join(session_dir, "llm_suggestion.pddl"),
        "domain": os.path.join(session_dir, "domain.pddl"),
        "problem": os.path.join(session_dir, "problem.pddl"),
        "planner_error": os.path.join(session_dir, "planner_error.txt"),
        "chat_history": os.path.join(session_dir, "chat_history.json"),
        "lore": os.path.join(session_dir, "lore.json"),
        "examples": os.path.join(session_dir, "examples_used.json")
    }

    # Caricamento piano
    try:
        plan = json.load(open(paths["plan"], encoding="utf-8")) \
            if os.path.exists(paths["plan"]) else None
    except json.JSONDecodeError as err:
        current_app.logger.warning("⚠️ Errore nel parsing di plan.json: %s", err)
        plan = None

    # Validazione
    validation_text = read_text_file(paths["validation"])
    try:
        validation_json = json.loads(validation_text) if validation_text else {}
    except json.JSONDecodeError as err:
        current_app.logger.warning("⚠️ Errore nel parsing di validation.json: %s", err)
        validation_json = {}

    # Altri contenuti
    domain = safe_content(paths["domain"], "(domain non disponibile)")
    problem = safe_content(paths["problem"], "(problem non disponibile)")
    planner_error = safe_content(paths["planner_error"])
    suggestion = safe_content(paths["suggestion"])

    # Refinement automatico se necessario
    if plan is None and planner_error and not suggestion:
        current_app.logger.info("🤖 Nessun piano trovato. Avvio riflessione automatica con LLM...")
        try:
            lore = json.load(open(paths["lore"], encoding="utf-8")) \
                if os.path.exists(paths["lore"]) else None
            refine_and_save(
                domain_path=paths["domain"],
                problem_path=paths["problem"],
                error_message=planner_error,
                output_dir=session_dir,
                lore=lore
            )
            suggestion = safe_content(paths["suggestion"])
            current_app.logger.info("✅ Riflessione completata.")
        except Exception as err:
            current_app.logger.warning("⚠️ Errore durante la riflessione automatica: %s", err)

    # Chat history
    chat_history = []
    if os.path.exists(paths["chat_history"]):
        try:
            with open(paths["chat_history"], encoding="utf-8") as f:
                chat_history = json.load(f)
        except json.JSONDecodeError as err:
            current_app.logger.warning("⚠️ Errore nel parsing di chat_history.json: %s", err)

    # Esempi RAG usati
    examples = []
    if os.path.exists(paths["examples"]):
        try:
            with open(paths["examples"], encoding="utf-8") as f:
                examples = json.load(f)
        except json.JSONDecodeError as err:
            current_app.logger.warning("⚠️ Errore nel parsing di examples_used.json: %s", err)

    return render_template(
        "result.html",
        plan=plan,
        validation=validation_text,
        validation_json=validation_json,
        suggestion=suggestion,
        domain=domain,
        problem=problem,
        planner_error=planner_error,
        session=session,
        chat_history=chat_history,
        examples=examples
    )
