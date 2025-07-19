import os, re, uuid, time, subprocess, logging, shutil, json, sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Union, List, Dict, Any
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
#MODEL = "llama3:8b-instruct-q5_K_M"
#MODEL = "llama3.2-vision"
#MODEL = "devstral:24b"
MODEL = "deepseek-coder-v2:16b"


# ----------------------------
# Funzioni principali
# ----------------------------
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


def ask_ollama(prompt: str, model: str = MODEL, num_ctx: int = 30000) -> str:
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
    # Assicurati che la cartella memory esista
    os.makedirs(db_dir, exist_ok=True)

    # Apri DB e crea tabella se serve
    conn = sqlite3.connect(db_path, check_same_thread=True)
    c = conn.cursor()
    c.execute("""
      CREATE TABLE IF NOT EXISTS checkpoints (
        thread_ts   INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id   TEXT,
        checkpoint  TEXT
      )
    """)
    # Serializza lo stato completo (inclusi domain/problem/tmp_dir/status...)
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

# def extract_section(text: str, section: str) -> Optional[str]:
#     """
#     Estrae la sezione `section` da un testo PDDL cercando:
#       1) '#### SECTION FILE' + code-block
#       2) i vari marker === … === o #### … #### come prima
#       3) marker semplificati === SECTION ===
#     """
#     # 1) Caso specifico: #### SECTION FILE + ```…```
#     file_pattern = (
#         rf"####\s*{re.escape(section)}\s*FILE\s*"   # '#### DOMAIN FILE' o '#### PROBLEM FILE'
#         r"\n```[^\n]*\n"                            # apertura del code‐block (```lang)
#         r"(?P<body>[\s\S]*?)"                      # contenuto non‐greedy
#         r"\n```"                                   # chiusura del code‐block
#     )
#     m = re.search(file_pattern, text, flags=re.IGNORECASE)
#     if m:
#         return m.group("body").strip()

#     # 2) Variante classica con START/END
#     variants = [
#         (r"^===\s*{sec}\s*START\s*===$",   r"^===\s*{sec}\s*END\s*===$"),
#         (r"^===\s*{sec}\s*START\s*===$",   r"^===\s*END\s*{sec}\s*===$"),
#         (r"^####\s*{sec}\s*START\s*####$", r"^####\s*{sec}\s*END\s*####$"),
#         (r"^####\s*{sec}\s*START\s*$",     r"^####\s*{sec}\s*END\s*$"),
#     ]
#     for start_pat, end_pat in variants:
#         sp = start_pat.format(sec=re.escape(section))
#         ep = end_pat.format(sec=re.escape(section))
#         pattern = (
#             rf"{sp}\s*\n"                          # marker di inizio
#             rf"(?:```[^\n]*\n)?"                   # optional opening fence
#             rf"(?P<body>[\s\S]*?)"                 # capture everything
#             rf"(?:\n```[^\n]*\n)?"                 # optional closing fence
#             rf"\s*{ep}"                            # marker di fine
#         )
#         match = re.search(
#             pattern,
#             text,
#             flags=re.DOTALL | re.IGNORECASE | re.MULTILINE
#         )
#         if match:
#             return match.group("body").strip()

#         # Estrai anche dentro fence Lisp-style
#         lisp_pattern = (
#             rf"```[^\n]*\n"                             # apertura fence: ```lang
#             rf"(?P<body>"                              
#                 rf"\(define\s*\({section.lower()}\b"  # inizio define (domain|problem)
#                 rf"[\s\S]*?"                           # qualsiasi contenuto non-greedy
#             rf")\n```"                                 # chiusura fence
#         )
#         m2 = re.search(lisp_pattern, text, flags=re.IGNORECASE)
#         if m2:
#             return m2.group("body").strip()

#     # 3) Nuova variante: marker semplificato === SECTION ===
#     simple_pattern = (
#         rf"^===\s*{re.escape(section)}\s*===\s*\n"  # === SECTION ===
#         rf"(?P<body>[\s\S]*?)"                      # tutto fino al prossimo marker
#         rf"(?=^===\s*[A-Z ]+\s*===\s*$)"            # lookahead su prossimo === ... ===
#     )
#     m3 = re.search(
#         simple_pattern,
#         text,
#         flags=re.DOTALL | re.IGNORECASE | re.MULTILINE
#     )
#     if m3:
#         return m3.group("body").strip()

#     return None

def strip_pddl_comments(text: str) -> str:
    return re.sub(r';[^\n]*', '', text)

def remove_markers(text: str) -> str:
    return re.sub(r'^===.*===\s*$', '', text, flags=re.MULTILINE)

# --- S-expression parser minimale ---
Token = Union[str, 'List[Token]']

def tokenize(s: str) -> List[str]:
    # Separiamo parentesi dai simboli
    return re.findall(r'\(|\)|[^\s()]+', s)

def parse_sexpr(tokens: List[str], i: int = 0) -> Tuple[Token, int]:
    if tokens[i] != '(':
        return tokens[i], i + 1
    lst = []
    i += 1  # salta '('
    while i < len(tokens) and tokens[i] != ')':
        elem, i = parse_sexpr(tokens, i)
        lst.append(elem)
    return lst, i + 1  # salta ')'

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

# --- Funzione principale ---
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

# def extract_section(text: str, section: str) -> Optional[str]:
#     """
#     Estrae la s-expression di (define (domain ...) … )
#     oppure di (define (problem ...) … ) da un testo PDDL.
#     Se non trova la chiusura per il domain, tronca al
#     prossimo '(define (problem' o al marker '=== PROBLEM ==='.
#     """
#     # 1) trova inizio
#     start_pat = rf"(?i)\(define\s*\(\s*{section}\b"
#     m = re.search(start_pat, text)
#     if not m:
#         return None
#     start_idx = m.start()
#     depth = 0

#     # 2) prova a bilanciare
#     for i, c in enumerate(text[start_idx:], start=start_idx):
#         if c == '(':
#             depth += 1
#         elif c == ')':
#             depth -= 1
#             if depth == 0:
#                 return text[start_idx : i+1].strip()

#     # 3) fallback per domain non bilanciato: cerca prima define(problem), poi marker
#     if section.lower() == "domain":
#         # a) define(problem)
#         pm = re.search(r"(?i)\(define\s*\(\s*problem\b", text, flags=re.IGNORECASE)
#         if pm:
#             return text[start_idx : pm.start()].strip()
#         # b) marker === PROBLEM ===
#         mk = re.search(r"(?i)^===\s*PROBLEM\s*===", text, flags=re.MULTILINE)
#         if mk:
#             return text[start_idx : mk.start()].strip()
#     # 4) fallback per problem non bilanciato: restituisci fino a fine testo
#     if section.lower() == "problem":
#         return text[start_idx:].strip()

#     return None

def extract_vision(raw_text: str) -> dict:
    # 0) Prova a estrarre il JSON dal code‐fence ```json … ```
    m = re.search(r"```json\s*([\s\S]*?)```", raw_text)
    if m:
        block = m.group(1)
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            pass  # fallback

    # 1) Estrai blocco JSON cercando il primo '{' prima di "description"
    idx = raw_text.find('"description"')
    if idx != -1:
        # cerca il '{' più vicino a sinistra
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
                            break  # fallback al parsing manuale

    # 2) Fallback manuale (come prima)
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
        else:  # actions
            chunks = re.split(r"\n\s*\d+\.\s*", text)
            acts = []
            for c in chunks:
                if "Parameters" in c or "Key preconditions" in c:
                    line = " ".join(c.splitlines())
                    line = re.sub(r"\*\*Key (?:preconditions|effects)\*\*:", "", line)
                    acts.append(clean(line))
            vision["actions"] = acts

    return vision


# def parse_vision_to_json(text: str) -> str:
#     """
#     Given the raw markdown vision output, extract INIT, GOAL, OBJECTS,
#     PLAN and ACTIONS sections and build a vision_spec JSON string.
#     """
#     vision_spec = {}

#     # helper to strip backticks and whitespace
#     def clean_pred(p): return p.strip(" `")

#     # 1) INIT
#     init_block = re.search(r"\*\*INIT state\*\*([\s\S]*?)\*\*GOAL", text)
#     vision_spec["init"] = []
#     if init_block:
#         for line in re.findall(r"•\s*`(.+?)`", init_block.group(1)):
#             vision_spec["init"].append(clean_pred(line))

#     # 2) GOAL
#     goal_block = re.search(r"\*\*GOAL state\*\*([\s\S]*?)\*\*OBJECTS", text)
#     vision_spec["goal"] = []
#     if goal_block:
#         for line in re.findall(r"•\s*`(.+?)`", goal_block.group(1)):
#             vision_spec["goal"].append(clean_pred(line))

#     # 3) OBJECTS
#     obj_block = re.search(r"\*\*OBJECTS\*\*([\s\S]*?)\*\*PLAN", text)
#     vision_spec["objects"] = []
#     if obj_block:
#         for line in re.findall(r"•\s*`?([^`\n]+?)`?$", obj_block.group(1), flags=re.M):
#             vision_spec["objects"].append(line.strip(" `"))

#     # 4) PLAN outline
#     plan_block = re.search(r"\*\*PLAN outline\*\*([\s\S]*?)\*\*ACTIONS", text)
#     vision_spec["plan"] = []
#     if plan_block:
#         for step in re.findall(r"\d+\.\s*`(.+?)`", plan_block.group(1)):
#             vision_spec["plan"].append(clean_pred(step))

#     # 5) ACTIONS (descriptive)
#     act_block = re.search(r"\*\*ACTIONS \(descriptive\)\*\*([\s\S]*?)(?:\*\*ROUTE SELECTION|\Z)", text)
#     vision_spec["actions"] = []
#     if act_block:
#         # split by blank line between actions
#         chunks = [c.strip() for c in act_block.group(1).split("\n\n") if c.strip()]
#         for chunk in chunks:
#             name = re.search(r"\*\*Name:\*\*\s*`?([^`]+?)`?", chunk)
#             params = re.search(r"\*\*Parameters:\*\*\s*`?([^`]+?)`?", chunk)
#             pre    = re.search(r"\*\*Key preconditions:\*\*\s*`?([^`]+?)`?", chunk)
#             eff    = re.search(r"\*\*Key effects:\*\*\s*`?([^`]+?)`?", chunk)
#             if name:
#                 action = {
#                     "name": name.group(1).strip(),
#                     "params": [p.strip() for p in params.group(1).split(",")] if params else [],
#                     "pre":   {"and": [p.strip() for p in pre.group(1).split(",")]} if pre else {"and": []},
#                     "eff":   {"add": [], "del": []}
#                 }
#                 # split effects into add vs del by looking for 'not '
#                 if eff:
#                     adds, dels = [], []
#                     for e in eff.group(1).split(","):
#                         e = e.strip()
#                         if e.startswith("not "):
#                             dels.append(e[len("not "):])
#                         else:
#                             adds.append(e)
#                     action["eff"]["add"] = adds
#                     action["eff"]["del"] = dels
#                 vision_spec["actions"].append(action)

#     return json.dumps(vision_spec, indent=2)

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