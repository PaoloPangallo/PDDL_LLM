# pylint: disable=missing-docstring,line-too-long,broad-except,unspecified-encoding


import os
import subprocess
import logging
import time
import requests

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "mistral"  # puoi cambiarlo se necessario


def create_session_dir(upload_folder: str) -> tuple[str, str]:
    import uuid
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(upload_folder, session_id)
    os.makedirs(session_dir, exist_ok=True)
    return session_id, session_dir


def run_planner(session_dir: str, timeout: int = 60) -> tuple[bool, str]:
    try:
        start = time.time()
        result = subprocess.run(
            ["bash", "./planner/run-planner.sh", session_dir],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        elapsed = time.time() - start
        logger.info(f"⏱️ Fast Downward completato in {elapsed:.2f}s")
        logger.debug(f"STDOUT:\n{result.stdout}")
        logger.debug(f"STDERR:\n{result.stderr}")

        # Salva log completo del planner (stdout + stderr)
        log_path = os.path.join(session_dir, "planner.log")
        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write(result.stdout)
            log_file.write("\n--- STDERR ---\n")
            log_file.write(result.stderr)

        # Salva solo l'errore in planner_error.txt
        error_path = os.path.join(session_dir, "planner_error.txt")
        with open(error_path, "w", encoding="utf-8") as err_file:
            err_file.write(result.stderr.strip())

        success = result.returncode == 0
        return success, result.stderr.strip()

    except subprocess.TimeoutExpired:
        logger.error("❌ Fast Downward ha superato il timeout.")
        error_path = os.path.join(session_dir, "planner_error.txt")
        with open(error_path, "w", encoding="utf-8") as err_file:
            err_file.write("❌ Timeout del planner")
        return False, "❌ Timeout del planner"


def ask_ollama(prompt: str, model: str = MODEL, num_ctx: int = 4096) -> str:
    try:
        logger.info(f"📤 Invio prompt a Ollama con modello: {model} e num_ctx: {num_ctx}")
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
            timeout=(10, 360)  # 10s connessione, 6min max risposta
        )
        response.raise_for_status()
        result = response.json()
        return result.get("response", "").strip()

    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ HTTP Error da Ollama ({e.response.status_code}): {e.response.text.strip()}")
        logger.debug(f"📄 Prompt (primi 500 caratteri):\n{prompt[:500]}")
        raise

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Errore di rete con Ollama: {e}")
        logger.debug(f"📄 Prompt (primi 500 caratteri):\n{prompt[:500]}")
        raise

    except Exception as e:
        logger.error(f"❌ Errore generico durante la richiesta a Ollama: {e}")
        logger.debug(f"📄 Prompt (primi 500 caratteri):\n{prompt[:500]}")
        raise



def extract_between(text: str, start_marker: str, end_marker: str) -> str | None:
    try:
        start_idx = text.index(start_marker) + len(start_marker)
        end_idx = text.index(end_marker, start_idx)
        return text[start_idx:end_idx].strip()
    except ValueError:
        logger.warning(f"⚠️ Delimitatori non trovati: {start_marker} / {end_marker}")
        return None


def read_text_file(path: str) -> str | None:
    return open(path, encoding="utf-8").read() if os.path.exists(path) else None


def save_text_file(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
