"""
Modulo per il raffinamento automatico dei file PDDL tramite LLM locale (es. Ollama).
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional
import requests

from core.validator import validate_pddl
from core.utils import (
    read_text_file,
    save_text_file,
    extract_between,
)

# ===============================
# ⚙️ Configurazione
# ===============================
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
DEFAULT_MODEL = "llama3:8b-instruct-q5_K_M"
FALLBACK_MODEL = "mistral"
HEADERS = {"Content-Type": "application/json"}
DEBUG_LLM = True  # Attiva salvataggio completo per debug

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# ===============================
# 🔁 Invio prompt al LLM locale
# ===============================
def ask_local_llm(prompt: str, model: str) -> str:
    logger.info(" Invio richiesta a Ollama (%s)...", model)
    logger.debug(" Prompt inviato (primi 500 char):\n%s", prompt[:500])
    if len(prompt) > 4000:
        logger.warning("⚠️ Prompt molto lungo: %d caratteri", len(prompt))

    for attempt in range(3):
        try:
            resp = requests.post(
                OLLAMA_URL,
                json={"model": model, "prompt": prompt, "stream": False},
                headers=HEADERS,
                timeout=(10, 720)
            )
            if resp.status_code != 200:
                logger.error(" Ollama ha risposto con %d:\n%s", resp.status_code, resp.text)
            resp.raise_for_status()
            try:
                data = resp.json()
            except json.JSONDecodeError:
                logger.error(" Risposta non in formato JSON valido:\n%s", resp.text)
                raise RuntimeError("Risposta Ollama non è in formato JSON valido.")
            return data.get("response", "").strip()

        except requests.RequestException as err:
            logger.error(" Tentativo %d fallito con %s (%s)", attempt + 1, model, err, exc_info=True)

    return None


def ask_llm_with_fallback(prompt: str) -> str:
    response = ask_local_llm(prompt, model=DEFAULT_MODEL)
    if response:
        return response

    logger.warning("💡 Fallback attivato: riprovo con modello '%s'", FALLBACK_MODEL)
    response = ask_local_llm(prompt, model=FALLBACK_MODEL)
    if response:
        return response

    Path("llm_debug").mkdir(exist_ok=True)
    Path("llm_debug/failed_prompt.txt").write_text(prompt, encoding="utf-8")
    raise RuntimeError("Errore critico: LLM non ha risposto nemmeno con fallback.")


# ===============================
#  Costruzione del prompt
# ===============================
def build_prompt(domain_text: str, problem_text: str, error_message: str, validation: Optional[dict] = None, lore: Optional[dict] = None) -> str:
    prompt_path = Path("prompts/reflection_prompt.txt")
    if prompt_path.exists():
        template = prompt_path.read_text(encoding="utf-8")
    else:
        logger.warning("⚠️ Template reflection_prompt.txt mancante, uso fallback minimale.")
        template = (
            "### DOMAIN FILE:\n{domain}\n\n"
            "### PROBLEM FILE:\n{problem}\n\n"
            "### ERROR MESSAGE:\n{error_message}\n\n"
            "### SUGGESTED FIX:\nFornisci una nuova versione corretta dei file."
            "\n=== DOMAIN START ===\n<...>\n=== DOMAIN END ==="
            "\n=== PROBLEM START ===\n<...>\n=== PROBLEM END ==="
        )

    #  Note generali per l’LLM
    notes = "\n\n OBIETTIVO:\n"
    notes += "- Correggi i file PDDL affinché siano validi, completi e coerenti con la pianificazione classica.\n"
    notes += "- NON inventare nuovi predicati, oggetti o tipi non presenti nei file originali.\n"
    notes += "- Mantieni la struttura delle azioni esistenti (nomi, parametri, logica) dove possibile.\n"
    notes += "- Aggiungi un commento (usando `;`) alla fine di ogni riga PDDL per spiegare cosa fa.\n"
    notes += "- Assicurati che ogni sezione obbligatoria (:types, :predicates, :init, :goal, ...) sia presente.\n"
    notes += "- Includi solo modifiche necessarie per far validare i file.\n"
    notes += "- NON rimuovere i commenti `;` presenti nei file se già corretti.\n"
    notes += "- Se aggiungi una nuova azione, documentala con un commento descrittivo.\n"
    notes += "- Rispetta la formattazione canonica del PDDL: indentazione e struttura chiara.\n"


    # 🔎 Errori semantici e specifici
    if isinstance(validation, dict):
        if validation.get("undefined_objects_in_goal"):
            notes += "\n🔹 Oggetti mancanti nel goal: " + ", ".join(validation["undefined_objects_in_goal"])
        if validation.get("semantic_errors"):
            notes += "\n Errori semantici rilevati:\n" + "\n".join(validation["semantic_errors"])
        if validation.get("missing_sections"):
            notes += "\n Sezioni mancanti: " + ", ".join(validation["missing_sections"])
        if validation.get("domain_mismatch"):
            notes += "\n Domain mismatch: " + validation["domain_mismatch"]

    # 🧠 Lore originale (se disponibile)
    if lore:
        try:
            lore_json = json.dumps(lore, indent=2, ensure_ascii=False)
            notes += f"\n LORE ORIGINALE:\n{lore_json}"
        except Exception:
            pass

    # 🔧 Errori noti
    if "unhashable type: 'list'" in error_message:
        notes += "\n Evita liste annidate nella sezione :init."

    # Costruzione prompt finale
    return template.format(
        domain=domain_text.strip(),
        problem=problem_text.strip(),
        error_message=error_message.strip() + notes,
        validation=json.dumps(validation, indent=2, ensure_ascii=False) if validation else ""
    )



# ===============================
#  Raffinamento dei file
# ===============================
def refine_pddl(
    domain_path: str,
    problem_path: str,
    error_message: str,
    lore: Optional[dict] = None,
    validation: Optional[dict] = None
) -> str:
    domain_raw = read_text_file(domain_path)
    problem_raw = read_text_file(problem_path)

    if not domain_raw or not problem_raw:
        raise ValueError("❌ File PDDL vuoti o mancanti.")

    # Se non passato esplicitamente, fai la validazione qui
    if validation is None and lore is not None:
        validation = validate_pddl(domain_raw, problem_raw, lore)

    if validation and validation.get("valid_syntax", True) and not validation.get("semantic_errors"):
        logger.info("✅ Nessun errore significativo, refine non necessario.")
        return (
            "=== DOMAIN START ===\n" + domain_raw + "\n=== DOMAIN END ===\n"
            "=== PROBLEM START ===\n" + problem_raw + "\n=== PROBLEM END ==="
        )

    prompt = build_prompt(domain_raw, problem_raw, error_message, validation, lore)
    return ask_llm_with_fallback(prompt)

# ===============================
# 💾 Raffina e salva
# ===============================
def refine_and_save(domain_path: str, problem_path: str, error_message: str, output_dir: str, lore: Optional[dict] = None) -> tuple[Optional[str], Optional[str]]:
    from core.utils import get_unique_filename

    os.makedirs(output_dir, exist_ok=True)

    try:
        suggestion_raw = refine_pddl(domain_path, problem_path, error_message, lore)
    except Exception as err:
        err_msg = f"❌ Errore durante il raffinamento: {str(err)}"
        logger.error(err_msg, exc_info=True)
        save_text_file(os.path.join(output_dir, "refinement_error.txt"), err_msg)
        return None, None

    if DEBUG_LLM:
        save_text_file(os.path.join(output_dir, "llm_raw_output.txt"), suggestion_raw)

    domain_suggestion = extract_between(suggestion_raw, "=== DOMAIN START ===", "=== DOMAIN END ===")
    problem_suggestion = extract_between(suggestion_raw, "=== PROBLEM START ===", "=== PROBLEM END ===")

    if domain_suggestion is None or problem_suggestion is None:
        logger.error("❌ Delimitatori mancanti nell'output LLM.")

    if lore:
        validation = validate_pddl(domain_suggestion or "", problem_suggestion or "", lore)
        save_text_file(os.path.join(output_dir, "validation.json"), json.dumps(validation, indent=2))

    if not domain_suggestion or not domain_suggestion.strip().lower().startswith("(define"):
        logger.warning("⚠️ DOMAIN non valido. Output salvato.")
        save_text_file(os.path.join(output_dir, "refinement_error.txt"), "Dominio non valido o mancante")
        return None, None

    domain_path_out = get_unique_filename(output_dir, "llm_domain")
    save_text_file(domain_path_out, domain_suggestion.strip())

    problem_path_out = None
    if problem_suggestion and problem_suggestion.strip().lower().startswith("(define"):
        problem_path_out = get_unique_filename(output_dir, "llm_problem")
        save_text_file(problem_path_out, problem_suggestion.strip())

    logger.info("✅ Raffinamento completato e salvato.")
    return domain_suggestion, problem_suggestion
