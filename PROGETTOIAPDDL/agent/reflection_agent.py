"""Modulo per il raffinamento automatico dei file PDDL tramite LLM locale (Ollama)."""

import os
import json
import logging
import requests
from pathlib import Path
from typing import Optional

from game.validator import validate_pddl
from game.utils import (
    read_text_file,
    save_text_file,
    extract_between,
)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
DEFAULT_MODEL = "mistral"
HEADERS = {"Content-Type": "application/json"}

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def ask_local_llm(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Invia un prompt a Ollama e restituisce la risposta testuale."""
    logger.info("🤖 Invio richiesta a Ollama...")
    logger.debug("📤 Prompt inviato:\n%s", prompt[:500])
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": model, "prompt": prompt, "stream": False},
            headers=HEADERS,
            timeout=(10, 360)
        )
        resp.raise_for_status()
        data = resp.json()
        answer = data.get("response", "").strip()
        if not answer:
            logger.warning("⚠️ Nessuna risposta generata dall'LLM.")
        return answer
    except Exception as e:
        logger.error("❌ Errore nella richiesta a Ollama: %s", e, exc_info=True)
        raise


def build_prompt(domain_text: str, problem_text: str, error_message: str, validation: Optional[dict] = None) -> str:
    """Costruisce un prompt dettagliato e resiliente da dominio, problema e messaggio d'errore."""
    template_path = Path("prompts/reflection_prompt.txt")
    if not template_path.exists():
        raise FileNotFoundError("Prompt template mancante: prompts/reflection_prompt.txt")
    prompt_template = template_path.read_text(encoding="utf-8")

    additional_notes = "\n\n🎯 OBIETTIVO:\n"
    additional_notes += (
        "- Correggi i file domain.pddl e problem.pddl in modo che siano validi, coerenti e completi.\n"
        "- Se ci sono oggetti o predicati nel goal non definiti, definiscili tu nel dominio o negli oggetti.\n"
        "- Se il lore è incompleto, inventa entità coerenti per completare l'inizializzazione o gli obiettivi.\n"
        "- NON lasciare sezioni mancanti: tutti i blocchi devono essere inclusi e ben formattati.\n"
        "- Inserisci sempre almeno un'azione sensata, e assicurati che i predicati usati nelle azioni siano dichiarati.\n"
        "- Evita nomi con apici ('), spazi o simboli speciali.\n"
        "- I blocchi DOMAIN e PROBLEM devono iniziare con (define ...) e terminare in modo completo.\n"
    )

    if "unhashable type: 'list'" in error_message:
        additional_notes += (
            "\n⚠️ ERROR HINT: Evita liste annidate o tuple nella sezione :init."
            " Ogni fatto deve essere nella forma piatta: (predicato argomento1 argomento2 ...).\n"
        )

    if isinstance(validation, dict):
        if validation.get("undefined_objects_in_goal"):
            missing = ", ".join(validation["undefined_objects_in_goal"])
            additional_notes += (
                f"\n🧩 Oggetti usati nel goal ma non definiti: {missing}. Aggiungili in modo coerente.\n"
            )
        if validation.get("semantic_errors"):
            additional_notes += "\n⚠️ Errori semantici rilevati:\n" + "\n".join(validation["semantic_errors"])

    return prompt_template.format(
        domain=domain_text.strip(),
        problem=problem_text.strip(),
        error_message=error_message.strip() + additional_notes,
        validation=json.dumps(validation, indent=2, ensure_ascii=False) if validation else ""
    )



def refine_pddl(domain_path: str, problem_path: str, error_message: str,
                lore: Optional[dict] = None, model: str = DEFAULT_MODEL) -> str:
    """Invoca l'LLM per proporre una versione corretta dei file PDDL."""
    domain_text = read_text_file(domain_path)
    problem_text = read_text_file(problem_path)

    fallback_dir = Path(domain_path).parent
    save_text_file(fallback_dir / "original_domain.pddl", domain_text)
    save_text_file(fallback_dir / "original_problem.pddl", problem_text)

    logger.debug("📄 DOMAIN ORIGINALE:\n%s", domain_text[:500])
    logger.debug("📄 PROBLEM ORIGINALE:\n%s", problem_text[:500])

    if not domain_text or not problem_text:
        raise ValueError("❌ I file domain.pddl o problem.pddl sono vuoti o mancanti.")

    validation = validate_pddl(domain_text, problem_text, lore) if lore else None
    logger.info("🔁 LLM invoked with error: %s", error_message.strip()[:80])
    logger.info("🧠 Validation summary: %s", json.dumps(validation or {}, indent=2)[:500])

    prompt = build_prompt(domain_text, problem_text, error_message, validation)
    return ask_local_llm(prompt, model)


def refine_and_save(domain_path: str, problem_path: str, error_message: str,
                    output_dir: str, lore: Optional[dict] = None):
    """Esegue il raffinamento PDDL e salva i file suggeriti nella directory di output."""
    from game.utils import get_unique_filename  # ✅ import ritardato per evitare import circolari

    suggestion_raw = refine_pddl(domain_path, problem_path, error_message, lore)

    domain_suggestion = extract_between(
        suggestion_raw, "=== DOMAIN START ===", "=== DOMAIN END ===")
    problem_suggestion = extract_between(
        suggestion_raw, "=== PROBLEM START ===", "=== PROBLEM END ===")

    os.makedirs(output_dir, exist_ok=True)
    raw_output_path = os.path.join(output_dir, "llm_raw_output.txt")
    save_text_file(raw_output_path, suggestion_raw)

    if not domain_suggestion or not problem_suggestion:
        logger.warning("⚠️ Output LLM incompleto o malformato:\n%s", suggestion_raw[:500])

    if not domain_suggestion:
        raise ValueError("❌ DOMAIN block not found.")
    if not domain_suggestion.strip().lower().startswith("(define"):
        raise ValueError("❌ DOMAIN non valido. Controlla 'llm_raw_output.txt'")

    domain_path_out = get_unique_filename(output_dir, "llm_domain")
    save_text_file(domain_path_out, domain_suggestion.strip())

    if problem_suggestion and problem_suggestion.strip().lower().startswith("(define"):
        problem_path_out = get_unique_filename(output_dir, "llm_problem")
        save_text_file(problem_path_out, problem_suggestion.strip())

    logger.info("✅ Suggestions saved in %s", output_dir)
    return domain_suggestion, problem_suggestion
