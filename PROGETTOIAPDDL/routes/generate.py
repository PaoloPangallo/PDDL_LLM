# app/routes/generate.py
import os
import json
import logging
from flask import Blueprint, request, redirect, url_for, current_app
from agent.reflection_agent import refine_and_save
from game.validator import validate_pddl
from game.utils import create_session_dir, run_planner, read_text_file, save_text_file
from game.generator import build_prompt_from_lore, ask_ollama, extract_between

generate_bp = Blueprint("generate", __name__)

@generate_bp.route("/generate", methods=["POST"])
def generate_from_lore():
    lore_path = request.form.get("lore_path")
    run = request.form.get("run") == "true"

    if not lore_path or not os.path.exists(lore_path):
        return "❌ Lore file mancante o invalido.", 400

    session_id, session_dir = create_session_dir(current_app.config["UPLOAD_FOLDER"])

    try:
        current_app.logger.info("🧠 Avvio generate_pddl_from_lore()")

        # 1. Lettura lore e salvataggio
        with open(lore_path, encoding="utf-8") as f:
            lore = json.load(f)
        lore_session_path = os.path.join(session_dir, "lore.json")
        with open(lore_session_path, "w", encoding="utf-8") as f:
            json.dump(lore, f, indent=2, ensure_ascii=False)

        # 2. Generazione prompt e risposta LLM
        prompt, used_examples = build_prompt_from_lore(lore)
        raw = ask_ollama(prompt)


        # 3. Salva risposta grezza
        raw_path = os.path.join(session_dir, "raw_llm_response.txt")
        try:
            save_text_file(raw_path, raw)
        except Exception as err:
            current_app.logger.warning(f"⚠️ Impossibile salvare raw LLM response: {err}")

        # 4. Parsing blocchi DOMAIN/PROBLEM
        domain = extract_between(raw, "=== DOMAIN START ===", "=== DOMAIN END ===")
        problem = extract_between(raw, "=== PROBLEM START ===", "=== PROBLEM END ===")

        if not domain or not problem:
            raise ValueError("❌ PDDL non generati correttamente: controlla se la risposta include i blocchi richiesti.")

        # 5. Salvataggio PDDL
        domain_path = os.path.join(session_dir, "domain.pddl")
        problem_path = os.path.join(session_dir, "problem.pddl")
        save_text_file(domain_path, domain)
        save_text_file(problem_path, problem)
        current_app.logger.info("✅ File PDDL salvati.")

        # 6. Validazione statica
        validation = validate_pddl(domain, problem, lore)
        save_text_file(os.path.join(session_dir, "validation.json"), json.dumps(validation, indent=2))

        # 7. Esecuzione planner (se richiesto)
        if run:
            current_app.logger.info("⚙️ Avvio run_planner()")
            planner_success, planner_error = run_planner(session_dir)

            # 8. Salvataggio errore del planner
            error_path = os.path.join(session_dir, "planner_error.txt")
            save_text_file(error_path, planner_error)

            # 9. Refinement automatico se fallisce
            if not planner_success:
                try:
                    suggestion_path = os.path.join(session_dir, "llm_suggestion.pddl")
                    refine_and_save(domain_path, problem_path, planner_error, suggestion_path, lore)
                except Exception as refine_error:
                    current_app.logger.error(f"❌ Fallita la raffinazione automatica: {refine_error}")

    except Exception as e:
        current_app.logger.exception("❌ Errore in generate_from_lore()")
        return f"❌ Errore generazione: {e}", 500

    return redirect(url_for("result.result", session=session_id))
