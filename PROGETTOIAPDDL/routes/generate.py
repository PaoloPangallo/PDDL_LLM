"""Modulo Flask per la generazione automatica di file PDDL da lore.json (via path o upload) e upload manuale PDDL."""

import os
import json
import shutil
from flask import Blueprint, request, redirect, url_for, current_app, jsonify
from agent.reflection_agent import refine_and_save
from game.validator import validate_pddl
from game.utils import create_session_dir, run_planner, read_text_file, save_text_file
from game.generator import generate_pddl_from_dict

generate_bp = Blueprint("generate", __name__)
LORE_DIR = "lore"

@generate_bp.route("/generate", methods=["POST"])
def generate_from_lore():
    """
    Accetta un lore.json (via path o file), genera i file PDDL, li salva, li valida,
    ed eventualmente esegue planner e raffinazione.
    """
    lore_path = request.form.get("lore_path")
    lore_file = request.files.get("lore_file")
    run = request.form.get("run") == "true"

    lore = None

    # 🧩 Caricamento lore via path
    if lore_path and os.path.exists(lore_path):
        try:
            with open(lore_path, encoding="utf-8") as f:
                lore = json.load(f)
        except Exception as e:
            current_app.logger.error("❌ Errore apertura file lore_path: %s", e)
            return "❌ Errore apertura file lore_path.", 400

    # 📁 Caricamento lore via upload
    elif lore_file:
        try:
            lore = json.load(lore_file)
        except Exception as e:
            current_app.logger.error("❌ Errore parsing JSON da file caricato: %s", e)
            return "❌ Il file lore caricato non è un JSON valido.", 400

    else:
        return "❌ Devi fornire un percorso valido o caricare un file lore.json.", 400

    # ✅ Creazione cartella sessione
    title = lore.get("title") or lore.get("description") or "session"
    session_id, session_dir = create_session_dir(
        current_app.config["UPLOAD_FOLDER"], title
    )

    # 💾 Salvataggio lore nella sessione
    lore_session_path = os.path.join(session_dir, "lore.json")
    with open(lore_session_path, "w", encoding="utf-8") as f:
        json.dump(lore, f, indent=2, ensure_ascii=False)

    # ⚙️ Generazione PDDL
    domain, problem, _ = generate_pddl_from_dict(lore, lore_path or "from_upload.json")

    if not domain or not problem or not domain.strip().lower().startswith("(define"):
        save_text_file(os.path.join(session_dir, "domain.pddl"), domain or "❌ Domain PDDL non generato.")
        save_text_file(os.path.join(session_dir, "problem.pddl"), problem or "❌ Problem PDDL non generato.")
        save_text_file(os.path.join(session_dir, "validation.json"), json.dumps({
            "error": "❌ PDDL non generati correttamente: controlla i blocchi richiesti."
        }, indent=2))
        return redirect(url_for("result.result", session=session_id))

    save_text_file(os.path.join(session_dir, "domain.pddl"), domain)
    save_text_file(os.path.join(session_dir, "problem.pddl"), problem)

    # 🔎 Validazione
    validation = validate_pddl(domain, problem, lore)
    save_text_file(os.path.join(session_dir, "validation.json"), json.dumps(validation, indent=2))

    # 🚀 Planner e Refine
    if run:
        success, error_msg = run_planner(session_dir)
        save_text_file(os.path.join(session_dir, "planner_error.txt"), error_msg)

        if not success:
            try:
                shutil.copy(os.path.join(session_dir, "domain.pddl"), os.path.join(session_dir, "original_domain.pddl"))
                shutil.copy(os.path.join(session_dir, "problem.pddl"), os.path.join(session_dir, "original_problem.pddl"))

                refine_and_save(
                    os.path.join(session_dir, "domain.pddl"),
                    os.path.join(session_dir, "problem.pddl"),
                    error_msg,
                    session_dir,
                    lore
                )
            except Exception as refine_error:
                current_app.logger.error("❌ Fallita la raffinazione automatica: %s", refine_error)

    return redirect(url_for("result.result", session=session_id))


@generate_bp.route("/upload", methods=["POST"])
def manual_upload():
    """Upload manuale di domain.pddl e problem.pddl."""
    domain_file = request.files.get("domain")
    problem_file = request.files.get("problem")

    if not domain_file or not problem_file:
        return "❌ Entrambi i file PDDL sono richiesti.", 400

    session_id, session_dir = create_session_dir(current_app.config["UPLOAD_FOLDER"], "manual")

    domain_path = os.path.join(session_dir, "domain.pddl")
    problem_path = os.path.join(session_dir, "problem.pddl")
    domain_file.save(domain_path)
    problem_file.save(problem_path)

    domain_txt = read_text_file(domain_path)
    problem_txt = read_text_file(problem_path)
    validation = validate_pddl(domain_txt, problem_txt, lore={})
    save_text_file(os.path.join(session_dir, "validation.json"), json.dumps(validation, indent=2))

    run_planner(session_dir)

    return redirect(url_for("result.result", session=session_id))


@generate_bp.route("/api/lore_titles", methods=["GET"])
def get_lore_titles():
    """Restituisce i titoli dei file lore disponibili nella directory lore/."""
    titles = []
    try:
        for filename in os.listdir(LORE_DIR):
            if filename.endswith(".json"):
                filepath = os.path.join(LORE_DIR, filename)
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                    title = data.get("quest_title") or data.get("title") or data.get("description") or filename
                    titles.append({
                        "title": title,
                        "filename": filepath.replace("\\", "/")
                    })
        current_app.logger.info(f"✅ Trovate {len(titles)} lore.")
    except Exception as e:
        current_app.logger.exception("❌ Errore in get_lore_titles:")
        return jsonify({"error": str(e)}), 500

    return jsonify(titles)
