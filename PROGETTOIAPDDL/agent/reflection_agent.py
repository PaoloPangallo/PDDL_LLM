"""
Modulo per il raffinamento automatico dei file PDDL tramite LLM locale (es. Ollama).
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional

import requests

from game.validator import validate_pddl
from game.utils import (
    read_text_file,
    save_text_file,
    extract_between,
)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
#DEFAULT_MODEL = "llama3.2-vision"
#DEFAULT_MODEL = "deepseek-r1:8b"
#DEFAULT_MODEL = "codellama:13b"
DEFAULT_MODEL = "deepseek-coder-v2:16b"
#DEFAULT_MODEL = "starcoder:15b"

HEADERS = {"Content-Type": "application/json"}

logger = logging.getLogger(__name__)
#if not logger.hasHandlers():
#    handler = logging.StreamHandler()
#    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
#    handler.setFormatter(formatter)
#    logger.addHandler(handler)
#    logger.setLevel(logging.INFO)


def ask_local_llm(prompt: str, model: str = DEFAULT_MODEL, num_ctx: int = 40000) -> str:
    """Invia un prompt a Ollama e restituisce la risposta testuale."""
    logger.info("📤 Invio prompt a Ollama con modello: %s e num_ctx: %d", model, num_ctx)
    logger.debug(f"📤 Prompt Refiner inviato:\n{prompt[:700]}...\n")

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_keep": 0,  # <-- Questo resetta il contesto nei modelli compatibili
                "num_ctx": num_ctx
        }
        },
        headers=HEADERS
    )
    response.raise_for_status()
    data = response.json()
    answer = data.get("response", "").strip()
    if not answer:
        logger.warning("⚠️ Nessuna risposta generata dall'LLM.")
    return answer


def build_prompt(domain_text: str, problem_text: str, error_message: str, validation: Optional[dict] = None, lore: Optional[dict] = None) -> str:
    """Costruisce un prompt dettagliato e resiliente da dominio, problema e messaggio d'errore."""
    template_path = Path("prompts/reflection_prompt_v2.txt")
    if not template_path.exists():
        raise FileNotFoundError("Prompt template mancante: prompts/reflection_prompt.txt")
    prompt_template = template_path.read_text(encoding="utf-8")

    validation_summary = ""
    valid_syntax = True
    if isinstance(validation, dict):
        validation_summary = validation.get("validation_summary", "")
        valid_syntax = validation.get("valid_syntax", "")

    lines = [line.lstrip("\t") for line in validation_summary.splitlines() if line.strip()]
    clean_summary = "\n".join(lines)
    # Prepara la lista di errori di sintassi (missing_sections)
    # syntax_list = []
    # if isinstance(validation, dict) and not validation.get("valid_syntax", True):
    #     for sec in validation.get("missing_sections", []):
    #         syntax_list.append(f"- Missing section `{sec}`")
    # syntax_txt = "\n".join(syntax_list) if syntax_list else "No syntax errors found."

    # Prepara il report strutturato e dettagliato
    # report_lines = []
    # if isinstance(validation, dict) and validation.get("errors"):
    #     for e in validation["errors"]:
    #         kind = e.get("kind", "unknown")
    #         sec = e.get("section", "?")
    #         detail = e.get("detail", "")
    #         pred = e.get("predicate", "")
    #         occurrence = e.get("occurrence", "")
    #         suggestion = e.get("suggestion", "")
    #         report_lines.append(
    #             f"- Kind: {kind}\n"
    #             f"  Section: {sec}\n"
    #             f"  Predicate: {pred}\n"
    #             f"  Occurrence: {occurrence}\n"
    #             f"  Detail: {detail}\n"
    #             f"  Suggestion: {suggestion}\n"
    #         )
    # report_txt = "\n".join(report_lines) if report_lines else "No structural errors found."

    # Aggiungi errori semantici se presenti
    # if isinstance(validation, dict) and validation.get("semantic_errors"):
    #     sem_lines = "\n".join(f"- {e}" for e in validation["semantic_errors"])
    #     report_txt += f"\n\nSemantic Errors:\n{sem_lines}"

    lore_txt = json.dumps(lore, indent=2) if lore else "No lore provided."

    # return prompt_template.format(
    #     syntax_errors=syntax_txt,
    #     validation_report=report_txt,
    #     error_message=error_message,
    #     domain=domain_text.strip(),
    #     problem=problem_text.strip(),
    #     lore=lore_txt
    # )
    return prompt_template.format_map({
        #"syntax_errors": syntax_txt,
        "validation_summary": clean_summary,
        "valid_syntax": valid_syntax,
        "error_message": error_message,
        "domain": domain_text.strip(),
        "problem": problem_text.strip(),
        "lore": lore_txt
    })



def refine_pddl(domain: str, problem: str, error_message: str, lore: Optional[dict] = None, model: str = DEFAULT_MODEL) -> str:
    """Invoca l'LLM per proporre una versione corretta dei file PDDL."""
    #domain_raw = read_text_file(domain_path)
    #problem_raw = read_text_file(problem_path)
    if not domain or not problem:
        raise ValueError("❌ I file domain o problem sono vuoti o mancanti.")

    validation = validate_pddl(domain, problem, lore) if lore else None

    prompt = build_prompt(
        domain_text=domain,
        problem_text=problem,
        error_message=error_message,
        validation=validation,
        lore=lore
    )

    # Chiamata all'LLM
    answer = ask_local_llm(prompt, model)
    return answer


def refine_and_save(
    domain_path: str,
    problem_path: str,
    error_message: str,
    output_dir: str,
    lore: Optional[dict] = None
) -> tuple[Optional[str], Optional[str]]:
    """Esegue il raffinamento PDDL e salva i file suggeriti nella directory di output."""
    os.makedirs(output_dir, exist_ok=True)
    try:
        suggestion_raw = refine_pddl(domain_path, problem_path, error_message, lore)
    except Exception as err:
        err_msg = f"❌ Errore durante il raffinamento: {err}"
        logger.error(err_msg, exc_info=True)
        save_text_file(os.path.join(output_dir, "refinement_error.txt"), err_msg)
        return None, None

    save_text_file(os.path.join(output_dir, "llm_raw_output.txt"), suggestion_raw)

    domain_sugg = extract_between(suggestion_raw, "=== DOMAIN START ===", "=== DOMAIN END ===")
    problem_sugg = extract_between(suggestion_raw, "=== PROBLEM START ===", "=== PROBLEM END ===")
    return domain_sugg, problem_sugg
