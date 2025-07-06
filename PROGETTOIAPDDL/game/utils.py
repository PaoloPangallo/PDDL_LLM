"""Modulo di utilità per la generazione, esecuzione e interazione con planner e LLM."""

# pylint: disable=missing-docstring,line-too-long,broad-except,unspecified-encoding

import os
import re
import uuid
import time
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional

import requests

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
#MODEL = "llama3.2-vision"
#MODEL = "deepseek-r1:8b"
MODEL = "deepseek-coder-v2:16b"
#MODEL = "codellama:13b"


def create_session_dir(upload_folder: str, name_hint: Optional[str] = None) -> tuple[str, str]:
    """Crea una directory di sessione con nome univoco basato su timestamp e hint."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    # qui assicuriamo sempre una str, anche se name_hint è None
    hint = (name_hint or "").strip().lower().replace(" ", "_")
    base = re.sub(r"[^\w\-]", "", hint)[:30] if hint else "session"
    session_id = f"{base}-{timestamp}-{uuid.uuid4().hex[:6]}"
    path = os.path.join(upload_folder, session_id)
    os.makedirs(path, exist_ok=True)
    return session_id, path


def run_planner(session_dir: str, timeout: int = 60) -> Tuple[bool, str]:
    """
    Esegue lo script del planner Fast Downward su una directory di sessione.

    Args:
        session_dir (str): Directory contenente i file PDDL.
        timeout (int): Timeout massimo in secondi per il planner.

    Returns:
        Tuple[bool, str]: True se il planner ha avuto successo, False altrimenti, con messaggio di errore o stderr.
    """
    planner_script = Path("planner/run-planner.sh")
    session_path = Path(session_dir)
    log_path = session_path / "planner.log"
    error_path = session_path / "planner_error.txt"

    if not planner_script.exists():
        logger.error("❌ Planner script non trovato: %s", planner_script)
        error_msg = f"❌ Script non trovato: {planner_script}"
        error_path.write_text(error_msg, encoding="utf-8")
        return False, error_msg

    try:
        start = time.time()  # ⬅️ AGGIUNTO
        result = subprocess.run(
            ["bash", str(planner_script), str(session_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
    )


        elapsed = time.time() - start
        logger.info("⏱️ Planner terminato in %.2fs (exit code: %d)", elapsed, result.returncode)
        logger.debug("STDOUT:\n%s", result.stdout)
        logger.debug("STDERR:\n%s", result.stderr)

        # Salva log completo
        log_content = result.stdout + "\n--- STDERR ---\n" + result.stderr
        log_path.write_text(log_content, encoding="utf-8")

        # Salva errore se presente
        error_path.write_text(result.stderr.strip(), encoding="utf-8")

        success = result.returncode == 0 and "found legal plan" in result.stdout.lower()
        return success, result.stderr.strip() if not success else ""

    except subprocess.TimeoutExpired:
        logger.error("❌ Timeout del planner (%ds)", timeout)
        error_path.write_text("❌ Timeout del planner", encoding="utf-8")
        return False, "❌ Timeout del planner"

    except Exception as e:
        logger.exception("❌ Errore durante l'esecuzione del planner")
        error_path.write_text(f"❌ Errore interno: {e}", encoding="utf-8")
        return False, f"❌ Errore interno: {e}"

def ask_ollama(prompt: str, model: str = MODEL, num_ctx: int = 40000) -> str:
    """Invia un prompt a Ollama e restituisce la risposta del modello."""
    try:
        logger.info("📤 Invio prompt a Ollama con modello: %s e num_ctx: %d", model, num_ctx)
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_ctx": num_ctx
                }
            },
            timeout=(10, 360)
        )
        response.raise_for_status()
        result = response.json()
        return result.get("response", "").strip()

    except requests.exceptions.HTTPError as e:
        logger.error("❌ HTTP Error da Ollama (%s): %s", e.response.status_code, e.response.text.strip())
        #logger.debug("📄 Prompt (primi 500 caratteri):\n%s", prompt[:500])
        raise

    except requests.exceptions.RequestException as e:
        logger.error("❌ Errore di rete con Ollama: %s", e)
        #logger.debug("📄 Prompt (primi 500 caratteri):\n%s", prompt[:500])
        raise

    except Exception as e:
        logger.error("❌ Errore generico durante la richiesta a Ollama: %s", e)
        #logger.debug("📄 Prompt (primi 500 caratteri):\n%s", prompt[:500])
        raise


def extract_between(text: str, start_marker: str, end_marker: str) -> str | None:
    """Estrae la porzione di testo tra due marcatori se presenti."""
    try:
        start_idx = text.index(start_marker) + len(start_marker)
        end_idx = text.index(end_marker, start_idx)
        return text[start_idx:end_idx].strip()
    except ValueError:
        logger.warning("⚠️ Delimitatori non trovati: %s / %s", start_marker, end_marker)
        return None


def read_text_file(path: str) -> str | None:
    """Legge un file di testo se esiste e ne restituisce il contenuto."""
    return open(path, encoding="utf-8").read() if os.path.isfile(path) else None


def save_text_file(path: str, content: str) -> None:
    """Salva una stringa in un file, sollevando eccezione se il path è una directory."""
    if os.path.isdir(path):
        raise IsADirectoryError(f"❌ Il path {path} è una directory, impossibile salvarci un file.")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
      
def get_unique_filename(folder: str, base_name: str, ext: str = ".pddl") -> str:
    """Genera un nome file univoco nella cartella specificata."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base_path = Path(folder) / f"{base_name}-{timestamp}{ext}"
    counter = 1
    while base_path.exists():
        base_path = Path(folder) / f"{base_name}-{timestamp}-{counter}{ext}"
        counter += 1
    return str(base_path)
