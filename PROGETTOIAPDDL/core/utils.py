import os, re, uuid, time, subprocess, logging, shutil, json, sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Union, List, Dict, Any
import requests

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

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
#MODEL = "llama3:8b-instruct-q5_K_M"
#MODEL = "llama3.2-vision"
#MODEL = "devstral:24b"
#MODEL = "deepseek-coder-v2:16b"


def create_session_dir(upload_folder: str, name_hint: Optional[str] = None) -> tuple[str, str]:
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


#def ask_ollama(prompt: str, model: str = MODEL, num_ctx: int = 30000) -> str:
def ask_ollama(prompt: str, model: str, num_ctx: int = 30000) -> str:
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
            timeout=(10, 3600)
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

def read_text_file(path: str) -> str | None:
    return open(path, encoding="utf-8").read() if os.path.isfile(path) else None


def save_text_file(path: str, content: str) -> None:
    if os.path.isdir(path):
        raise IsADirectoryError(f"❌ Il path {path} è una directory, impossibile salvarci un file.")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def save_pipeline_state(thread_id: str, state: Dict[str, Any]) -> None:
    """Persisti l'ultimo PipelineState nella tabella checkpoints."""
    db_dir = "memory"
    db_path = f"{db_dir}/{thread_id}.sqlite"
    os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_path, check_same_thread=True)
    c = conn.cursor()
    c.execute("""
      CREATE TABLE IF NOT EXISTS checkpoints (
        thread_ts   INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id   TEXT,
        checkpoint  TEXT
      )
    """)
    serialized = json.dumps(state, ensure_ascii=False)
    c.execute("""
      INSERT INTO checkpoints(thread_id, checkpoint)
      VALUES (?, ?)
    """, (thread_id, serialized))
    conn.commit()
    conn.close()


def get_unique_filename(folder: str, base_name: str, ext: str = ".pddl") -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base_path = Path(folder) / f"{base_name}-{timestamp}{ext}"
    counter = 1
    while base_path.exists():
        base_path = Path(folder) / f"{base_name}-{timestamp}-{counter}{ext}"
        counter += 1
    return str(base_path)

def extract_between(text: str, start: str, end: str) -> Optional[str]:
    """Estrae il contenuto tra due marker, rimuovendo blocchi Markdown come ```pddl ... ``` se presenti."""
    
    pattern = rf"{re.escape(start)}\s*(.*?)\s*{re.escape(end)}"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)

    if match:
        content = match.group(1).strip()
        if content.startswith("```"):
            content = re.sub(r"^```[a-zA-Z]*\n?", "", content)
            content = re.sub(r"\n?```$", "", content)
        return content.strip()

    return None

def strip_pddl_comments(text: str) -> str:
    return re.sub(r';[^\n]*', '', text)

def remove_markers(text: str) -> str:
    return re.sub(r'^===.*===\s*$', '', text, flags=re.MULTILINE)

Token = Union[str, 'List[Token]']

def tokenize(s: str) -> List[str]:
    return re.findall(r'\(|\)|[^\s()]+', s)

def parse_sexpr(tokens: List[str], i: int = 0) -> Tuple[Token, int]:
    if tokens[i] != '(':
        return tokens[i], i + 1
    lst = []
    i += 1
    while i < len(tokens) and tokens[i] != ')':
        elem, i = parse_sexpr(tokens, i)
        lst.append(elem)
    return lst, i + 1

def extract_define(sexprs: List[Token], section: str) -> Optional[Token]:
    for expr in sexprs:
        if (
            isinstance(expr, list)
            and len(expr) >= 2
            and expr[0] == 'define'
            and isinstance(expr[1], list)
            and expr[1][0] == section
        ):
            return expr
    return None

def sexpr_to_string(expr: Token) -> str:
    if isinstance(expr, str):
        return expr
    return '(' + ' '.join(sexpr_to_string(e) for e in expr) + ')'

def extract_section(text: str, section: str) -> Optional[str]:
    clean = strip_pddl_comments(text)
    clean = remove_markers(clean)
    tokens = tokenize(clean)
    sexprs = []
    i = 0
    while i < len(tokens):
        expr, i = parse_sexpr(tokens, i)
        sexprs.append(expr)
    define_expr = extract_define(sexprs, section)
    return sexpr_to_string(define_expr) if define_expr else None

def extract_vision(raw_text: str) -> dict:
    m = re.search(r"```json\s*([\s\S]*?)```", raw_text)
    if m:
        block = m.group(1)
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            pass

    idx = raw_text.find('"description"')
    if idx != -1:
        start = raw_text.rfind('{', 0, idx)
        if start != -1:
            depth = 0
            for i in range(start, len(raw_text)):
                if raw_text[i] == '{':
                    depth += 1
                elif raw_text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        candidate = raw_text[start:i+1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            break

    vision = {"init":[], "goal":[], "objects":[], "plan":[], "actions":[]}
    clean = lambda s: s.strip(" `").replace("= false","").replace("= true","").strip()
    sections = {
        "init":    r"\*\*INIT\*\*([\s\S]*?)\*\*GOAL\*\*",
        "goal":    r"\*\*GOAL\*\*([\s\S]*?)\*\*OBJECTS\*\*",
        "objects": r"\*\*OBJECTS\*\*([\s\S]*?)\*\*PLAN\*\*",
        "plan":    r"\*\*PLAN(?: outline)?\*\*([\s\S]*?)\*\*(?:ACTIONS|STEP)",
        "actions": r"\*\*ACTIONS[\s\S]*$"
    }
    for key, pat in sections.items():
        block = re.search(pat, raw_text, flags=re.M)
        if not block:
            continue
        text = block.group(1)
        if key in ("init","goal"):
            vision[key] = [
                clean(x) for x in re.findall(r"[•\-]\s*`?(.+?)`?", text)
            ]
        elif key == "objects":
            vision[key] = [
                clean(x) for x in re.findall(r"[•\-]\s*`?([^`\n]+?)`?", text)
            ]
        elif key == "plan":
            vision[key] = [
                clean(x) for x in re.findall(r"\d+\.\s*`?(.+?)`?", text)
            ]
        else:
            chunks = re.split(r"\n\s*\d+\.\s*", text)
            acts = []
            for c in chunks:
                if "Parameters" in c or "Key preconditions" in c:
                    line = " ".join(c.splitlines())
                    line = re.sub(r"\*\*Key (?:preconditions|effects)\*\*:", "", line)
                    acts.append(clean(line))
            vision["actions"] = acts

    return vision


domain_template_str = r"""
(define (domain {{ domain.name }})
    (:requirements :strips :typing{% if domain.actions | selectattr('pre.or') | list %} :adl{% endif %})
    (:types
    {% if domain.types %}
        {% for t in domain.types %}
        {{ t }}
        {% endfor %}
    {% else %}
        {% for t in domain.objects | map(attribute='type') | unique %}
        {{ t }}
        {% endfor %}
    {% endif %}
    )
    (:predicates
    {% for p in domain.predicates %}
        {{ p }}
    {% endfor %}
    )
    {% for action in domain.actions %}
    (:action {{ action.name }}
        :parameters (
        {% for p in action.params %}
        {{ p }}
        {% endfor %}
        )
        :precondition (and
        {% for lit in action.pre.and %}
            {% if lit.startswith('not ') %}
            (not ({{ lit[4:] }}))
            {% else %}
            ({{ lit }})
            {% endif %}
        {% endfor %}
        {% if action.pre.or %}
        (or
            {% for lit in action.pre.or %}
                {% if lit.startswith('not ') %}
                (not ({{ lit[4:] }}))
                {% else %}
                ({{ lit }})
                {% endif %}
            {% endfor %}
        )
        {% endif %}
        )
        :effect (and
        {% for a in action.eff.add %}
            ({{ a }})
        {% endfor %}
        {% for d in action.eff.del %}
            (not ({{ d }}))
        {% endfor %}
        )
    )
    {% endfor %}
)
""".strip()

problem_template_str = r"""
(define (problem {{ problem.name }})
    (:domain {{ problem.domain }})
    (:objects
        {% for obj in problem.objects %}
        {{ obj }}
        {% endfor %}
    )
    (:init
        {% for fact in problem.init %}
        ({{ fact }})
        {% endfor %}
    )
    (:goal (and
        {% for g in problem.goal %}
        ({{ g }})
        {% endfor %}
    ))
)
""".strip()