# app/routes/refine.py

import os
import json
from flask import Blueprint, request, redirect, url_for, current_app
from agents.reflection_agent import ask_local_llm, build_prompt
from core.validator import validate_pddl

from core.utils import (
    read_text_file,
    save_text_file,
    run_planner
)

refine_bp = Blueprint("refine", __name__)

@refine_bp.route("/regenerate", methods=["POST"])
def regenerate_with_refinement():
    session_id = request.form.get("session")
    if not session_id:
        return "❌ Session ID mancante", 400

    session_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], session_id)
    if not os.path.isdir(session_dir):
        return "❌ Sessione non valida", 400

    domain_path = os.path.join(session_dir, "domain.pddl")
    problem_path = os.path.join(session_dir, "problem.pddl")
    validation_path = os.path.join(session_dir, "validation.json")
    lore_path = os.path.join(session_dir, "lore.json")

    suggestion_path = os.path.join(session_dir, "llm_suggestion.pddl")
    problem_suggestion_path = os.path.join(session_dir, "llm_problem_suggestion.pddl")

    try:
        domain = read_text_file(domain_path)
        problem = read_text_file(problem_path)
        error_message = "Errore validazione PDDL"
        validation = json.load(open(validation_path)) if os.path.exists(validation_path) else None
        lore = json.load(open(lore_path)) if os.path.exists(lore_path) else None

        prompt = build_prompt(domain, problem, error_message, validation)
        suggestion = ask_local_llm(prompt)

        from core.utils import extract_between
        domain_suggestion = extract_between(suggestion, "=== DOMAIN START ===", "=== DOMAIN END ===")
        problem_suggestion = extract_between(suggestion, "=== PROBLEM START ===", "=== PROBLEM END ===")

        if not domain_suggestion or not domain_suggestion.strip().lower().startswith("(define"):
            raise ValueError("❌ Il blocco DOMAIN non è valido o mancante.")

        save_text_file(suggestion_path, domain_suggestion.strip())

        if problem_suggestion and problem_suggestion.strip().lower().startswith("(define"):
            save_text_file(problem_suggestion_path, problem_suggestion.strip())

        current_app.logger.info("✅ Nuovi suggerimenti salvati.")

    except Exception as e:
        current_app.logger.exception("❌ Errore nella rigenerazione con LLM")
        return f"Errore durante la rigenerazione: {e}", 500

    return redirect(url_for("result.result", session=session_id))



@refine_bp.route("/apply_fix", methods=["POST"])
def apply_fix():
    session = request.form.get("session")
    if not session:
        return "❌ Session ID mancante", 400

    session_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], session)
    suggestion_path = os.path.join(session_dir, "llm_suggestion.pddl")
    problem_suggestion_path = os.path.join(session_dir, "llm_problem_suggestion.pddl")
    domain_path = os.path.join(session_dir, "domain.pddl")
    problem_path = os.path.join(session_dir, "problem.pddl")
    lore_path = os.path.join(session_dir, "lore.json")

    if not os.path.exists(suggestion_path):
        return "❌ Nessun suggerimento trovato da applicare", 404

    # ✅ Applica suggerimento DOMAIN
    domain = read_text_file(suggestion_path)
    if domain:
        save_text_file(domain_path, domain.strip())
    else:
        return "❌ Il file suggerimento dominio è vuoto o non leggibile", 400

    # ✅ Applica suggerimento PROBLEM se esiste
    if os.path.exists(problem_suggestion_path):
        problem = read_text_file(problem_suggestion_path)
        if problem and problem.strip().lower().startswith("(define"):
            save_text_file(problem_path, problem.strip())
        else:
            current_app.logger.warning("⚠️ llm_problem_suggestion.pddl presente ma non valido. Uso il file esistente.")
    else:
        current_app.logger.info("ℹ️ Nessun suggerimento alternativo per problem.pddl. Mantengo quello esistente.")

    # 📋 Ricarica contenuti e lore
    domain = read_text_file(domain_path)
    problem = read_text_file(problem_path)
    lore = json.load(open(lore_path, encoding="utf-8")) if os.path.exists(lore_path) else {}

    # ✅ Valida e salva
    validation_result = validate_pddl(domain, problem, lore)
    save_text_file(os.path.join(session_dir, "validation.json"), json.dumps(validation_result, indent=2))

    # ⚙️ Esegui planner
    plan_success, planner_error = run_planner(session_dir)
    if plan_success:
        current_app.logger.info("✅ Piano generato con successo.")
    else:
        save_text_file(os.path.join(session_dir, "planner_error.txt"), planner_error)

    return redirect(url_for("result.result", session=session))
