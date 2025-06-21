"""Modulo Flask per la generazione automatica di file PDDL da lore.json e upload manuale."""

import os
import json
from flask import Blueprint, request, redirect, url_for, current_app
from agent.reflection_agent import refine_and_save
from game.validator import validate_pddl
from game.utils import create_session_dir, run_planner, read_text_file, save_text_file
from game.generator import generate_pddl_from_dict

generate_bp = Blueprint("generate", __name__)


@generate_bp.route("/generate", methods=["POST"])
def generate_from_lore():
    """
    Riceve un lore.json, genera i file PDDL, li salva e li valida.
    Esegue il planner e la raffinazione automatica se richiesto.
    """
    lore_path = request.form.get("lore_path")
    run = request.form.get("run") == "true"

    if not lore_path or not os.path.exists(lore_path):
        return "❌ Lore file mancante o invalido.", 400

    try:
        with open(lore_path, encoding="utf-8") as f:
            lore = json.load(f)

        title = lore.get("title") or lore.get("description") or "session"
        session_id, session_dir = create_session_dir(
            current_app.config["UPLOAD_FOLDER"], title
        )

        lore_session_path = os.path.join(session_dir, "lore.json")
        with open(lore_session_path, "w", encoding="utf-8") as f:
            json.dump(lore, f, indent=2, ensure_ascii=False)

        domain, problem, _ = generate_pddl_from_dict(lore, lore_path)

        if not domain or not problem or not domain.strip().lower().startswith("(define"):
            save_text_file(
                os.path.join(session_dir, "domain.pddl"),
                domain or "❌ Domain PDDL non generato."
            )
            save_text_file(
                os.path.join(session_dir, "problem.pddl"),
                problem or "❌ Problem PDDL non generato."
            )
            save_text_file(
                os.path.join(session_dir, "validation.json"),
                json.dumps({
                    "error": (
                        "❌ PDDL non generati correttamente: controlla se la risposta "
                        "include i blocchi richiesti."
                    )
                }, indent=2)
            )
            return redirect(url_for("result.result", session=session_id))

        save_text_file(os.path.join(session_dir, "domain.pddl"), domain)
        save_text_file(os.path.join(session_dir, "problem.pddl"), problem)

        validation = validate_pddl(domain, problem, lore)
        save_text_file(
            os.path.join(session_dir, "validation.json"),
            json.dumps(validation, indent=2)
        )

        if run:
            success, error_msg = run_planner(session_dir)
            save_text_file(os.path.join(session_dir, "planner_error.txt"), error_msg)

            if not success:
                try:
                    refine_and_save(
                        os.path.join(session_dir, "domain.pddl"),
                        os.path.join(session_dir, "problem.pddl"),
                        error_msg,
                        os.path.join(session_dir, "llm_suggestion.pddl"),
                        lore
                    )
                except Exception as refine_error:  # mantenuto generico per fallback
                    current_app.logger.error(
                        "❌ Fallita la raffinazione automatica: %s", refine_error
                    )

    except (json.JSONDecodeError, OSError) as e:
        current_app.logger.exception("❌ Errore in generate_from_lore(): %s", e)
        return f"❌ Errore generazione: {e}", 500

    return redirect(url_for("result.result", session=session_id))


@generate_bp.route("/upload", methods=["POST"])
def manual_upload():
    """
    Consente all'utente di caricare manualmente domain.pddl e problem.pddl.
    Esegue la validazione e il planner.
    """
    domain_file = request.files.get("domain")
    problem_file = request.files.get("problem")

    if not domain_file or not problem_file:
        return "❌ Entrambi i file PDDL sono richiesti.", 400

    session_id, session_dir = create_session_dir(
        current_app.config["UPLOAD_FOLDER"], "manual"
    )

    domain_path = os.path.join(session_dir, "domain.pddl")
    problem_path = os.path.join(session_dir, "problem.pddl")
    domain_file.save(domain_path)
    problem_file.save(problem_path)

    domain_txt = read_text_file(domain_path)
    problem_txt = read_text_file(problem_path)
    validation = validate_pddl(domain_txt, problem_txt, lore={})
    save_text_file(
        os.path.join(session_dir, "validation.json"),
        json.dumps(validation, indent=2)
    )

    run_planner(session_dir)

    return redirect(url_for("result.result", session=session_id))
