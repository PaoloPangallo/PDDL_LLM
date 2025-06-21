"""Modulo per il raffinamento automatico dei file PDDL tramite LLM locale (Ollama)."""

import os
import json
import shutil
import logging
import requests
from pathlib import Path

from game.validator import validate_pddl
from game.utils import read_text_file, save_text_file, extract_between

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

def build_prompt(domain: str, problem: str, error_message: str, validation: dict = None) -> str:
    """Costruisce un prompt dettagliato da dominio, problema e messaggio d'errore."""
    template_path = Path("prompts/reflection_prompt.txt")
    if not template_path.exists():
        raise FileNotFoundError("Prompt template mancante: prompts/reflection_prompt.txt")
    prompt_template = template_path.read_text(encoding="utf-8")

    return prompt_template.format(
        domain=domain,
        problem=problem,
        error_message=error_message,
        validation=json.dumps(validation, indent=2) if validation else ""
    )

def refine_pddl(domain_path: str, problem_path: str, error_message: str,
                lore: dict = None, model: str = DEFAULT_MODEL) -> str:
    """Invoca l'LLM per proporre una versione corretta dei file PDDL."""
    domain = read_text_file(domain_path)
    problem = read_text_file(problem_path)
    if not domain or not problem:
        raise ValueError("❌ I file domain.pddl o problem.pddl sono vuoti o mancanti.")

    validation = validate_pddl(domain, problem, lore) if lore else None
    logger.info("🔁 LLM invoked with error: %s", error_message.strip()[:80])
    logger.info("🧠 Validation summary: %s", json.dumps(validation or {}, indent=2)[:500])

    prompt = build_prompt(domain, problem, error_message, validation)
    return ask_local_llm(prompt, model)

def get_unique_filename(output_dir: str, base: str) -> str:
    i = 1
    while True:
        path = Path(output_dir) / f"{base}_{i}.pddl"
        if not path.exists():
            return str(path)
        i += 1

def refine_and_save(domain_path: str, problem_path: str, error_message: str,
                    output_dir: str, lore: dict = None):
    """Esegue il raffinamento PDDL e salva i file suggeriti nella directory di output."""
    suggestion_raw = refine_pddl(domain_path, problem_path, error_message, lore)

    domain_suggestion = extract_between(
        suggestion_raw, "=== DOMAIN START ===", "=== DOMAIN END ===")
    problem_suggestion = extract_between(
        suggestion_raw, "=== PROBLEM START ===", "=== PROBLEM END ===")

    os.makedirs(output_dir, exist_ok=True)
    raw_output_path = os.path.join(output_dir, "llm_raw_output.txt")
    save_text_file(raw_output_path, suggestion_raw)

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

if __name__ == "__main__":
    TEST_DOMAIN = "planner/test_plans/broken_domain.pddl"
    TEST_PROBLEM = "planner/test_plans/problem.pddl"
    TEST_ERROR = "Fast Downward: nessun piano trovato - azione 'move' irrealizzabile"

    print("🧠 Richiedo suggerimento all'LLM...\n")
    try:
        refined = refine_pddl(TEST_DOMAIN, TEST_PROBLEM, TEST_ERROR)
        print("✅ Suggerimento LLM:\n")
        print(refined)
    except Exception as e:
        print(f"❌ Errore: {e}")
