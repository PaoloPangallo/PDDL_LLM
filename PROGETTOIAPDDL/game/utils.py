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
from typing import Tuple, Optional, List
from tavily import TavilyClient
from pathlib import Path
import requests

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
#MODEL = "llama3.2-vision"
#MODEL = "deepseek-r1:8b"
#MODEL = "deepseek-coder-v2:16b"
#MODEL = "codellama:13b"
#MODEL = "starcoder:15b"
MODEL = "devstral:24b"

TAVILY_KEY = "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"
tavily = TavilyClient(api_key=TAVILY_KEY)

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

def extract_section(text: str, section: str) -> Optional[str]:
    """
    Estrae la sezione `section` da un testo PDDL cercando:
      1) '#### SECTION FILE' + code-block
      2) i vari marker === … === o #### … #### come prima
    """
    # 1) Caso specifico: #### SECTION FILE + ```…```
    file_pattern = (
        rf"####\s*{re.escape(section)}\s*FILE\s*"   # '#### DOMAIN FILE' o '#### PROBLEM FILE'
        r"\n```[^\n]*\n"                            # apertura del code‐block (```lang)
        r"(?P<body>[\s\S]*?)"                      # contenuto non‐greedy
        r"\n```"                                   # chiusura del code‐block
    )
    m = re.search(file_pattern, text, flags=re.IGNORECASE)
    if m:
        return m.group("body").strip()

    variants = [
        (r"^===\s*{sec}\s*START\s*===$",   r"^===\s*{sec}\s*END\s*===$"),
        (r"^===\s*{sec}\s*START\s*===$",   r"^===\s*END\s*{sec}\s*===$"),
        (r"^####\s*{sec}\s*START\s*####$", r"^####\s*{sec}\s*END\s*####$"),
        (r"^####\s*{sec}\s*START\s*$",     r"^####\s*{sec}\s*END\s*$"),
    ]
    for start_pat, end_pat in variants:
        sp = start_pat.format(sec=re.escape(section))
        ep = end_pat.format(sec=re.escape(section))
        pattern = (
            rf"{sp}\s*\n"                          # marker di inizio
            rf"(?:```[^\n]*\n)?"                   # optional opening fence
            rf"(?P<body>[\s\S]*?)"                 # capture everything
            rf"(?:\n```[^\n]*\n)?"                 # optional closing fence
            rf"\s*{ep}"                            # marker di fine
        )
        match = re.search(pattern, text, flags=re.DOTALL | re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group("body").strip()

        lisp_pattern = (
            rf"```[^\n]*\n"                             # apertura fence: ```lang
            rf"(?P<body>"                              
                rf"\(define\s*\({section.lower()}\b"  # inizio define (domain|problem)
                rf"[\s\S]*?"                           # qualsiasi contenuto non-greedy
            rf")\n```"                                 # chiusura fence
        )   
        m = re.search(lisp_pattern, text, flags=re.IGNORECASE)
        if m:
            return m.group("body").strip()
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

def strip_pddl_artifacts(text: str) -> str:
    lines = text.splitlines()
    cleaned_lines = []
    in_fence = False
    for line in lines:
        if re.match(r"^```(?:lisp)?", line.strip()):
            in_fence = not in_fence
            continue        
        if line.lstrip().startswith(";"):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def load_few_shot_examples(examples_root: str, max_examples: int = 3) -> List[str]:
    """
    Scorre examples_root, per ogni sottocartella che somiglia a un esempio:
      - legge domain.pddl e problem.pddl (e, se esiste, plan.txt)
      - costruisce una stringa formattata === DOMAIN START === ... === PROBLEM END ===
    Ritorna al più max_examples esempi.
    """
    examples = []
    root = Path(examples_root)
    for ex_dir in sorted(root.iterdir()):
        if not ex_dir.is_dir():
            continue

        dom = ex_dir / "domain.pddl"
        prob = ex_dir / "problem.pddl"
        plan = ex_dir / "plan.txt"

        if not (dom.exists() and prob.exists()):
            continue

        dom_txt  = dom.read_text(encoding="utf-8")
        prob_txt = prob.read_text(encoding="utf-8")
        plan_txt = plan.read_text(encoding="utf-8") if plan.exists() else None

        chunk = []
        chunk.append(f"--- EXAMPLE ({ex_dir.name}) ---")
        chunk.append("=== DOMAIN START ===")
        chunk.append(dom_txt.rstrip())
        chunk.append("=== DOMAIN END ===\n")
        chunk.append("=== PROBLEM START ===")
        chunk.append(prob_txt.rstrip())
        chunk.append("=== PROBLEM END ===")
        if plan_txt:
            chunk.append("\n=== PLAN ===")
            chunk.append(plan_txt.rstrip())
        examples.append("\n".join(chunk))

        if len(examples) >= max_examples:
            break

    return examples


def fetch_pddl_refs(query: str, top_k: int = 3) -> List[str]:
    """
    Interroga Tavily e ritorna una lista di stringhe '- Title — URL'.
    """
    # es: search_depth="basic" o "advanced"
    resp = tavily.search(query=query, search_depth="basic", max_results=top_k)
    results = resp.get("results", [])  # lista di DocumentSummary
    formatted = [f"- {doc['title']} — {doc['url']}" for doc in results]
    return formatted


def fetch_pddl_snippet(url: str, max_tokens: int = 500, top_k_sentences: int = 3) -> str:
    """
    Usa get_search_context per recuperare un estratto del documento URL.
    Poi tronca alle prime top_k_sentences.
    """
    # chiedi a Tavily un contesto limitato a max_tokens
    full_text = tavily.get_search_context(
        query=url,
        search_depth="basic",
        max_tokens=max_tokens,
    )
    # ora estrai le prime frasi
    sentences = full_text.split(". ")
    snippet = ". ".join(sentences[:top_k_sentences])
    return snippet + (" …" if len(sentences) > top_k_sentences else "")