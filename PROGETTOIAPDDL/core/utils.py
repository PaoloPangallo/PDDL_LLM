import os
import re
import uuid
import time
import subprocess
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import requests

# ----------------------------
# Setup Logging globale
# ----------------------------
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    file_handler = logging.FileHandler("questmaster.log", encoding="utf-8")
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)

# ----------------------------
# Configurazione LLM
# ----------------------------
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "llama3:8b-instruct-q5_K_M"

#MODEL = "llama3:8b-instruct-q5_K_M"
#MODEL = "devstral:24b"
MODEL = "deepseek-coder-v2:16b"


# ----------------------------
# Funzioni principali
# ----------------------------
def create_session_dir(upload_folder: str, name_hint: str = None) -> tuple[str, str]:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = name_hint.strip().lower().replace(" ", "_") if name_hint else "session"
    base = re.sub(r"[^\w\-]", "", base)[:30]
    session_id = f"{base}-{timestamp}-{uuid.uuid4().hex[:6]}"
    path = os.path.join(upload_folder, session_id)
    os.makedirs(path, exist_ok=True)
    return session_id, path


def clear_directory(folder: str) -> None:
    """Cancella e ricrea una cartella."""
    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.makedirs(folder, exist_ok=True)


def run_planner(session_dir: str, timeout: int = 60) -> Tuple[bool, str]:
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
        start = time.time()
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

        log_content = result.stdout + "\n--- STDERR ---\n" + result.stderr
        log_path.write_text(log_content, encoding="utf-8")
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


def ask_ollama(prompt: str, model: str = MODEL, num_ctx: int = 20480) -> str:
    try:
        logger.info("📤 Invio prompt a Ollama con modello: %s", model)
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_ctx": num_ctx}
            },
            timeout=(10, 720)
        )
        response.raise_for_status()
        result = response.json()
        return result.get("response", "").strip()

    except requests.exceptions.HTTPError as e:
        logger.error("❌ HTTP Error da Ollama (%s): %s", e.response.status_code, e.response.text.strip())
        _save_failed_prompt(prompt)
        raise

    except requests.exceptions.RequestException as e:
        logger.error("❌ Errore di rete con Ollama: %s", e)
        _save_failed_prompt(prompt)
        raise

    except Exception as e:
        logger.error("❌ Errore generico durante la richiesta a Ollama: %s", e)
        _save_failed_prompt(prompt)
        raise


def _save_failed_prompt(prompt: str):
    Path("llm_debug").mkdir(exist_ok=True)
    Path("llm_debug/last_failed_prompt.txt").write_text(prompt, encoding="utf-8")

logger = logging.getLogger(__name__)


def extract_between(text: str, start: str, end: str) -> Optional[str]:
    """Estrae il contenuto tra due marker, rimuovendo blocchi Markdown come ```pddl ... ``` se presenti."""
    
    # Primo tentativo: con o senza codice markdown
    pattern = rf"{re.escape(start)}\s*(.*?)\s*{re.escape(end)}"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)

    if match:
        content = match.group(1).strip()
        # Se inizia con ``` e finisce con ```, pulisci
        if content.startswith("```"):
            content = re.sub(r"^```[a-zA-Z]*\n?", "", content)
            content = re.sub(r"\n?```$", "", content)
        return content.strip()

    return None


def read_text_file(path: str) -> str | None:
    return open(path, encoding="utf-8").read() if os.path.isfile(path) else None


def save_text_file(path: str, content: str) -> None:
    if os.path.isdir(path):
        raise IsADirectoryError(f"❌ Il path {path} è una directory, impossibile salvarci un file.")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def get_unique_filename(folder: str, base_name: str, ext: str = ".pddl") -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base_path = Path(folder) / f"{base_name}-{timestamp}{ext}"
    counter = 1
    while base_path.exists():
        base_path = Path(folder) / f"{base_name}-{timestamp}-{counter}{ext}"
        counter += 1
    return str(base_path)
