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
    """Invia un prompt a Ollama e restituisce la risposta testuale, con retry e log esteso."""
    logger.info("🤖 Invio richiesta a Ollama...")
    logger.debug("📤 Prompt inviato (primi 500 caratteri):\n%s", prompt[:500])

    for attempt in range(3):  # retry fino a 3 volte
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
        except requests.RequestException as err:
            logger.error("❌ Tentativo %d fallito (%s)", attempt + 1, err, exc_info=True)

    # Dopo i retry → salvataggio di fallback
    timestamp = Path("llm_debug")
    timestamp.mkdir(parents=True, exist_ok=True)
    failed_path = timestamp / "failed_prompt.txt"
    failed_path.write_text(prompt, encoding="utf-8")
    logger.error("❌ Prompt salvato in %s per analisi manuale", failed_path)
    raise RuntimeError("Errore critico: l'LLM ha fallito tutte le risposte.")



def build_prompt(
    domain_text: str,
    problem_text: str,
    error_message: str,
    validation: Optional[dict] = None
) -> str:
    """Costruisce un prompt dettagliato e resiliente da dominio, problema e messaggio d'errore."""
    template_path = Path("prompts/reflection_prompt.txt")
    if not template_path.exists():
        raise FileNotFoundError("Prompt template mancante: prompts/reflection_prompt.txt")
    prompt_template = template_path.read_text(encoding="utf-8")

    additional_notes = "\n\n🎯 OBIETTIVO:\n"
    additional_notes += (
        "- Correggi i file domain.pddl e problem.pddl in modo che siano validi e coerenti.\n"
        "- Se mancano oggetti o predicati nel goal, aggiungili nel dominio o negli oggetti.\n"
        "- Evita simboli speciali o nomi non validi. Usa nomi semplici e coerenti.\n"
        "- Tutte le sezioni devono essere presenti e complete.\n"
    )

    if "unhashable type: 'list'" in error_message:
        additional_notes += (
            "\n⚠️ ERROR HINT: Evita liste annidate nella sezione :init. "
            "Ogni fatto deve essere nella forma piatta: (pred arg1 arg2).\n"
        )

    if isinstance(validation, dict):
        if validation.get("undefined_objects_in_goal"):
            missing = ", ".join(validation["undefined_objects_in_goal"])  # type: ignore
            additional_notes += f"\n🧩 Oggetti usati nel goal non definiti: {missing}\n"
        if validation.get("semantic_errors"):
            additional_notes += "\n⚠️ Errori semantici:\n" + "\n".join(validation["semantic_errors"])  # type: ignore

    return prompt_template.format(
        domain=domain_text.strip(),
        problem=problem_text.strip(),
        error_message=error_message.strip() + additional_notes,
        validation=json.dumps(validation, indent=2, ensure_ascii=False) if validation else ""
    )


def refine_pddl(
    domain_path: str,
    problem_path: str,
    error_message: str,
    lore: Optional[dict] = None,
    model: str = DEFAULT_MODEL
) -> str:
    """Invoca l'LLM per proporre una versione corretta dei file PDDL."""

    # Legge i file originali
    domain_raw = read_text_file(domain_path)
    problem_raw = read_text_file(problem_path)

    if not domain_raw or not problem_raw:
        raise ValueError("❌ I file domain.pddl o problem.pddl sono vuoti o mancanti.")

    # Backup file originali
    fallback_dir = Path(domain_path).parent
    save_text_file(fallback_dir / "original_domain.pddl", domain_raw)
    save_text_file(fallback_dir / "original_problem.pddl", problem_raw)

    # Validazione (se lore disponibile)
    validation = validate_pddl(domain_raw, problem_raw, lore) if lore else None

    logger.info("🔁 LLM invoked with error: %s", error_message.strip()[:80])
    logger.info("🧠 Validation summary: %s", json.dumps(validation or {}, indent=2)[:500])

    # Costruzione prompt
    prompt = build_prompt(
        domain_text=domain_raw,
        problem_text=problem_raw,
        error_message=error_message,
        validation=validation
    )

    # Invio a LLM
    return ask_local_llm(prompt, model)




def refine_and_save(
    domain_path: str,
    problem_path: str,
    error_message: str,
    output_dir: str,
    lore: Optional[dict] = None
) -> tuple[Optional[str], Optional[str]]:
    """Esegue il raffinamento PDDL e salva i file suggeriti nella directory di output."""
    from game.utils import get_unique_filename  # import ritardato

    os.makedirs(output_dir, exist_ok=True)

    try:
        suggestion_raw = refine_pddl(domain_path, problem_path, error_message, lore)
    except Exception as err:
        err_msg = f"❌ Errore durante il raffinamento: {str(err)}"
        logger.error(err_msg, exc_info=True)
        save_text_file(os.path.join(output_dir, "refinement_error.txt"), err_msg)
        return None, None

    save_text_file(os.path.join(output_dir, "llm_raw_output.txt"), suggestion_raw)

    domain_suggestion = extract_between(suggestion_raw, "=== DOMAIN START ===", "=== DOMAIN END ===")
    problem_suggestion = extract_between(suggestion_raw, "=== PROBLEM START ===", "=== PROBLEM END ===")

    if not domain_suggestion or not domain_suggestion.strip().lower().startswith("(define"):
        logger.warning("⚠️ DOMAIN mancante o malformato. Output salvato per revisione.")
        save_text_file(os.path.join(output_dir, "refinement_error.txt"), "Dominio non valido")
        return None, None

    domain_path_out = get_unique_filename(output_dir, "llm_domain")
    save_text_file(domain_path_out, domain_suggestion.strip())

    if problem_suggestion and problem_suggestion.strip().lower().startswith("(define"):
        problem_path_out = get_unique_filename(output_dir, "llm_problem")
        save_text_file(problem_path_out, problem_suggestion.strip())

    logger.info("✅ Suggerimenti salvati in %s", output_dir)
    return domain_suggestion, problem_suggestion
