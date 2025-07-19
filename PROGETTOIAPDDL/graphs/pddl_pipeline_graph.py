"""
PDDL pipeline graph: genera, valida e raffina file PDDL con persistenza SQLite.
"""

import os, json, logging, re, shutil, sqlite3, glob, tempfile
from pathlib import Path
from typing import Any, TypedDict, Optional, Dict, List, Annotated, cast
from jinja2 import Environment

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.types import interrupt, Command, Interrupt
from collections.abc import Mapping


# ────────────────────────────────────────────────────────────────────────────────
#  Configurazione logging (DEBUG di default)  ───────────────────────────────────
# ────────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger("pddl_pipeline_graph")

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
                    datefmt="%H:%M:%S")

def _log_node_start(name: str, state: Mapping[str, Any]):
    print(f"\n=== Enter {name} ===")
    print(f"Stato in ingresso: attempt={state.get('attempt')}, "
          f"status={state.get('status')}")
    logger.info(
        "  → %-16s | status: %-10s | attempt: %-3s",
        name, state.get("status", "–"), state.get("attempt", "–")
    )


def _log_node_end(name: str, extra: str = ""):
    print(f"=== Exit {name} ===\n")
    logger.info("  ← %-16s %s", name, extra if extra else "")
    logger.info("")

# ────────────────────────────────────────────────────────────────────────────────
#  Costanti (modelli e percorsi)  ───────────────────────────────────────────────
# ────────────────────────────────────────────────────────────────────────────────
VISION_PROMPT_PATH = Path("prompts/JsonGenerator/JsonGenerator3.txt")
SPEC_PROMPT_PATH   = Path("prompts/JsonIntermediator/Prompt3.txt")

# ────────────────────────────────────────────────────────────────────────────────
#  Import dal progetto
# ────────────────────────────────────────────────────────────────────────────────
from core.generator   import build_prompt_from_lore
from db.db            import retrieve_similar_examples_from_db
from core.utils       import ask_ollama, extract_section, save_text_file, extract_vision, domain_template_str, problem_template_str
from core.validator   import validate_pddl, generate_plan_with_fd
from agents.reflection_agent import refine_pddl

# ────────────────────────────────────────────────────────────────────────────────
#  Stato e politiche di merge
# ────────────────────────────────────────────────────────────────────────────────

def last(_old, new):
    return new

def non_empty_or_last(old, new):
    if new is None:
        return old
    if isinstance(new, str) and not new.strip():
        return old
    return new


class PipelineState(TypedDict):
    lore: Annotated[Dict[str, Any], last]
    thread_id: Annotated[str, last]

    tmp_dir: Annotated[Optional[str], last]

    # build‑prompt
    vision_json: Annotated[Optional[dict], last]
    spec_json: Annotated[Optional[dict], last]
    spec_raw: Annotated[Optional[str], last]

    # pddl
    prompt: Annotated[Optional[str], last]
    domain: Annotated[Optional[str], non_empty_or_last]
    problem: Annotated[Optional[str], non_empty_or_last]
    refined_domain: Annotated[Optional[str], non_empty_or_last]
    refined_problem: Annotated[Optional[str], non_empty_or_last]

    validation: Annotated[Optional[dict], last]
    error_message: Annotated[Optional[str], last]
    status: Annotated[Optional[str], last]

    attempt: Annotated[int, last]
    messages: Annotated[list[BaseMessage], last]#messages: Annotated[list[dict[str, str]], last]

    plan: Annotated[Optional[str], last]
    plan_log: Annotated[Optional[str], last]
    config: Annotated[Dict[str, Any], last]


# ────────────────────────────────────────────────────────────────────────────────
#  Helpers
# ────────────────────────────────────────────────────────────────────────────────
MAX_REFINE_ATTEMPTS = 0


def is_positive_feedback(msg: str) -> bool:
    return msg.strip().lower() in {
        "ok",
        "va bene",
        "accetto",
        "accetta",
        "perfetto",
        "tutto ok",
        "confermato",
    }


# ════════════════════════════════════════════════════════════════════════════════
#  NODI — Build‑Prompt (3 passaggi) con logging dettagliato
# ════════════════════════════════════════════════════════════════════════════════

def node_router(state: PipelineState) -> dict:
    """
    Decide il punto d'ingresso della pipeline in base allo stato.
    Se domain e problem sono già presenti (da un editing utente),
    salta alla validazione. Altrimenti, inizia dalla generazione del prompt.
    """
    # Controlla se siamo in modalità "resume con feedback" e i PDDL sono già stati forniti
    if state.get("_resume_with_feedback") and state.get("domain") and state.get("problem"):
        logger.info("➡️ [Router] Rilevata ripresa con PDDL utente, passando a Validate.")
        # Se riprendiamo, dobbiamo assicurarci che tmp_dir esista per i file PDDL
        tmp_dir = state.get("tmp_dir")
        if not tmp_dir:
            tmp_dir = tempfile.mkdtemp(prefix="pddl_")
            logger.debug("🧠 [Router] tmp_dir ricreata per resume: %s", tmp_dir)
        
        # Salva i PDDL forniti dall'utente nella tmp_dir per i nodi successivi
        save_text_file(os.path.join(tmp_dir, "domain.pddl"), state.get("domain") or "")
        save_text_file(os.path.join(tmp_dir, "problem.pddl"), state.get("problem") or "")

        return {
            "next_node": "Validate", # Indica al grafo di andare al nodo 'Validate'
            "tmp_dir": tmp_dir,
            "status": "ok"
        }
    else:
        logger.info("➡️ [Router] Inizio normale, passando a PreparePrompt.")
        return {
            "next_node": "PreparePrompt",
            "status": "ok"
        }

def node_prepare_prompt(state: PipelineState) -> PipelineState:
    name = "PreparePrompt"
    _log_node_start(name, state)

    attempt = -1
    cfg = state.get('config', {})
    lore_param = cfg.get('lore')
    custom_txt = cfg.get('custom_story')

    if lore_param is None:
        if state["lore"].get("preset"):
            lore_param = f"{state['lore']['id']}.json"
            custom_txt = None
        else:
            lore_param = "_free_"
            custom_txt = state["lore"]["text"]

    # 1) “testo libero” scelto nel front-end
    if lore_param == "_free_":
        lore_id   = "custom"
        lore_text = custom_txt or ""
        preset    = False

    # 2) è stato selezionato un file JSON (preset)
    else:
        lore_id   = Path(lore_param).stem
        lore_path = Path("lore") / lore_param
        lore_text = lore_path.read_text("utf-8")
        preset    = True
        
    thread_id = state["thread_id"]
    upload_dir = Path("static/uploads") / thread_id
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    logger.debug("%s | tmp_dir prepared at %s", name, upload_dir)

    new_state = {
        **state,
        "tmp_dir": str(upload_dir),
        "lore": {"text": lore_text},
        "status": "ok",
        "attempt": attempt,
    }
    _log_node_end(name)
    return cast(PipelineState, new_state)


def node_generate_vision(state: PipelineState) -> PipelineState:
    name = "GenerateVision"
    _log_node_start(name, state)
    if state.get("status") != "ok":
        logger.warning("%s | skipped (status=%s)", name, state.get("status"))
        return state

    template = VISION_PROMPT_PATH.read_text(encoding="utf-8")
    lore_txt = state["lore"]["text"]

    print("\n", lore_txt, "\n")

    logger.debug("%s | sending", name)
    raw = ask_ollama(template.replace("{{STORY}}", lore_txt))

    vision = extract_vision(raw)
    logger.debug("%s | vision extracted keys=%s", name, list(vision.keys()))

    new_state = {**state, "vision_json": vision, "status": "ok"}
    _log_node_end(name)
    return cast(PipelineState, new_state)


def node_generate_spec(state: PipelineState) -> PipelineState:
    name = "GenerateSpec"
    _log_node_start(name, state)
    if state.get("status") != "ok":
        logger.warning("%s | skipped (status=%s)", name, state.get("status"))
        return state

    inter_template = SPEC_PROMPT_PATH.read_text(encoding="utf-8")
    examples = "\n\n".join(
        Path(p).read_text(encoding="utf-8").strip() for p in glob.glob("examples/*.json")
    )
    spec_prompt = (
        inter_template.replace("{{VISION}}", json.dumps(state["vision_json"], indent=2))
        .replace("{{EXAMPLES}}", examples)
    )

    print("\n", spec_prompt[:500], "\n")

    logger.debug("%s | sending (prompt chars=%d)", name, len(spec_prompt))
    raw_out = ask_ollama(spec_prompt)

    clean = re.sub(r"^```(?:jsonc|json)?\n|\n```$", "", raw_out)
    try:
        spec = json.loads(clean)
        logger.info("%s | JSON spec parsed ✔", name)
        logger.info("")
        status, spec_raw = "ok", None
    except json.JSONDecodeError as e:
        logger.error("%s | JSON parse error: %s", name, e)
        spec, status, spec_raw = None, "failed", clean

    new_state = {
        **state,
        "spec_json": spec,
        "spec_raw": spec_raw,
        "status": status,
    }
    _log_node_end(name, extra=f"status={status}")
    return cast(PipelineState, new_state)


# ════════════════════════════════════════════════════════════════════════════════
#  Nodi pipeline (Generate → Validate → Refine …)
# ════════════════════════════════════════════════════════════════════════════════

def node_generate_pddl(state: PipelineState) -> PipelineState:
    name = "GeneratePDDL"
    _log_node_start(name, state)
    if state.get("status") != "ok":
        logger.warning("%s | skipped (status=%s)", name, state.get("status"))
        return {**state, "status": "failed", "error_message": "Skipped generate"}

    try:
        with open("prompts/generator/generator_prompt3.txt") as f:
            tmpl = f.read()
        spec_json_text = json.dumps(state["spec_json"], indent=2)
        final_prompt = tmpl.replace("{{SPEC_JSON}}", spec_json_text)

        print("\n", final_prompt[:500], "\n")

        logger.debug("%s | Prompt ready (chars=%d)", name, len(final_prompt))

        response = ask_ollama(prompt=final_prompt)
        logger.debug("%s | Response received (chars=%d)", name, len(response))

        tmp = state["tmp_dir"] or ""
        save_text_file(os.path.join(tmp, "raw_response.txt"), response)

        dom_raw = extract_section(response, "domain")
        prob_raw = extract_section(response, "problem")
        if not dom_raw or not prob_raw:
            raise ValueError("Formato PDDL non trovato")

        clean = lambda t: re.sub(r"```(?:\\w*\\n)?(.*?)```", r"\1", t, flags=re.DOTALL)
        domain, problem = clean(dom_raw), clean(prob_raw)

        save_text_file(os.path.join(tmp, "domain.pddl"), domain)
        save_text_file(os.path.join(tmp, "problem.pddl"), problem)
        logger.info("%s | PDDL files saved", name)
        logger.info("")

        new_state = {
            **state,
            "domain": domain,
            "problem": problem,
            "prompt": final_prompt,
            "status": "ok",
            "error_message": None,
            "refined_domain": None,
            "refined_problem": None,
        }
    except Exception as e:
        logger.exception("%s | error", name)
        new_state = {**state, "status": "failed", "error_message": f"Generate error: {e}"}

    _log_node_end(name, extra=f"status={new_state['status']}")
    return cast(PipelineState, new_state)

def node_validate(state: PipelineState) -> PipelineState:
    name = "Validate"
    _log_node_start(name, state)
    if state.get("status") != "ok":
        logger.warning("%s | skipped", name)
        return {**state, "status": "failed", "error_message": "Skipped validate"}

    if (state.get("attempt", -1) < 0):
        domain = state.get("domain") or ""
        problem = state.get("problem") or ""
        state["attempt"] = 0
    else:
        domain = state.get("refined_domain") or state.get("domain") or ""
        problem = state.get("refined_problem") or state.get("problem") or ""

        if domain == None or domain == "(define (domain ...))":
            domain = state.get("domain") or ""
    
        if problem == None or problem == "(define (problem ...))":
            problem = state.get("problem") or ""

    print("\n", domain, "\n")
    print("\n", problem, "\n")

    validation = validate_pddl(domain, problem, state["lore"])
    valid = validation.get("valid_syntax", False)
    sem_err = validation.get("semantic_errors", [])

    if valid and not sem_err:
        status, error = "ok", None
        logger.info("%s | validation OK", name)
        logger.info("")
    else:
        status, error = "failed", "Validation errors"
        logger.warning("%s | validation FAILED", name)

    new_state = {**state, "validation": validation, "status": status, "error_message": error}
    _log_node_end(name, extra=f"status={status}")
    return cast(PipelineState, new_state)


def node_refine(state: PipelineState) -> PipelineState:
    name = "Refine"
    _log_node_start(name, state)
    if state.get("status") != "failed":
        logger.info("%s | skip (status!=failed)", name)
        logger.info("")
        return state

    tmp = state.get("tmp_dir") or ""
    attempt = state.get("attempt", 0)

    dom_path = Path(tmp) / ("domain_refined.pddl" if attempt > 0 else "domain.pddl")
    prob_path = Path(tmp) / ("problem_refined.pddl" if attempt > 0 else "problem.pddl")

    dom = dom_path.read_text(encoding="utf-8").strip()
    prob = prob_path.read_text(encoding="utf-8").strip()

    if dom == None or dom == "(define (domain ...))":
        dom_path = Path(tmp) / ("domain.pddl") or ""
    
    if prob == None or prob == "(define (problem ...))":
        prob_path = Path(tmp) / ("problem.pddl") or ""
    
    print("\n\n")
    print(dom_path)
    print("\n\n")
    print(prob_path)

    dom_path_str = str(dom_path)
    prob_path_str = str(prob_path)

    try:
        updated = refine_pddl(dom_path_str, prob_path_str,
                              error_message=state.get("error_message") or "",
                              lore=state["lore"])
        rd = extract_section(updated, "domain") or ""
        rp = extract_section(updated, "problem") or ""
        save_text_file(os.path.join(tmp, "domain_refined.pddl"), rd)
        save_text_file(os.path.join(tmp, "problem_refined.pddl"), rp)
        logger.info("%s | files refined and saved (attempt=%d)", name, attempt + 1)
        logger.info("")

        new_state = {
            **state,
            "refined_domain": rd,
            "refined_problem": rp,
            "attempt": attempt + 1,
            "status": "ok",
            "error_message": None,
        }
    except Exception:
        logger.exception("%s | refine error", name)
        new_state = {**state, "status": "failed", "error_message": "Refine error"}

    _log_node_end(name, extra=f"status={new_state['status']}")
    return cast(PipelineState, new_state)


# Decision helpers ---------------------------------------------------------------

def validate_decision(state: PipelineState) -> str:
    logger.debug("Decision | error_message=%s attempt=%s/%s",
                 state.get("error_message"), state.get("attempt"), MAX_REFINE_ATTEMPTS)
    em = state.get("error_message")
    attempt = state.get("attempt", 0)
    if not em:
        return "GeneratePlan"
    if attempt <= MAX_REFINE_ATTEMPTS:
        return "Refine"
    return "TemplateFallback" if state["lore"].get("preset") else "ChatFeedback"

def feedback_branch(state: PipelineState) -> Optional[str]:
    """
    Determina dove andare dopo ChatFeedback:
    - None se ancora in attesa di feedback (rimane nel nodo)  
    - "Validate" se ha ricevuto modifiche dall'utente
    """
    status = state.get("status")
    logger.debug("FeedbackBranch | status=%s", status)
    
    if status == "awaiting_feedback":
        return None
    elif status == "ok":
        return "Validate"
    else:
        logger.warning("FeedbackBranch | unexpected status: %s", status)
        return "Validate"

def plan_branch(state: PipelineState) -> str:
    return "ChatFeedback" if state.get("status") == "failed" else "End"

# ────────────────────────────────────────────────────────────────────
#  Nodo ChatFeedback – blocca il grafo finché l’utente non risponde
# ────────────────────────────────────────────────────────────────────
def node_chat_feedback(state: PipelineState) -> PipelineState | Interrupt:
    """
    • Al primo passaggio invia domain / problem al frontend e si mette
      in stato "awaiting_feedback".
    • Nei passaggi successivi mantiene lo stato completo finché
      non arriva un HumanMessage contenente i nuovi PDDL.
    • Quando riceve le modifiche resetta lo stato di errore e riparte
      verso la validazione.
    """
    name = "ChatFeedback"
    _log_node_start(name, state)

    # ───── 1) appena entrati (non eravamo in attesa) ──────────────
    if state.get("status") != "awaiting_feedback":
        dom  = state.get("refined_domain")  or state.get("domain")  or ""
        prob = state.get("refined_problem") or state.get("problem") or ""

        new_state = {
            **state,  # ✅ MANTIENI TUTTO LO STATO ESISTENTE
            "status":  "awaiting_feedback",
            "domain":  dom,
            "problem": prob,
        }
        _log_node_end(name, extra="waiting for UI edit")
        payload = {"domain": dom, "problem": prob}
        return interrupt(payload)

    # ───── 2) siamo già in attesa → controlla se l'utente ha risposto
    messages = state.get("messages", [])
    edited_msg = None
    
    # Cerca il messaggio più recente dall'utente
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            edited_msg = msg
            break
    
    if not edited_msg:
        _log_node_end(name, extra="still waiting (no new message)")
        # ✅ MANTIENI LO STATO COMPLETO invece di restituire {}
        return cast(PipelineState, state)

    # ───── 3) l'utente ha inviato i PDDL modificati ───────────────
    try:
        payload = json.loads(str(edited_msg.content))
        dom_new = payload.get("domain", "")
        prob_new = payload.get("problem", "")

        if not dom_new or not prob_new:
            _log_node_end(name, extra="invalid payload - missing domain/problem")
            return cast(PipelineState, state)

        print("\nDominio Ricevuto:\n")
        print(dom_new)
        print("\nProblema Ricevuto:\n")
        print(prob_new)

    except (json.JSONDecodeError, KeyError) as e:
        logger.error("%s | bad payload format: %s", name, e)
        _log_node_end(name, extra=f"bad payload ({e})")
        return cast(PipelineState, state)

    # Salva i file modificati
    tmp_dir = state.get("tmp_dir") or ""
    if tmp_dir:
        try:
            save_text_file(os.path.join(tmp_dir, "domain_ui.pddl"), dom_new)
            save_text_file(os.path.join(tmp_dir, "problem_ui.pddl"), prob_new)
            logger.info("%s | UI-modified files saved", name)
        except Exception as e:
            logger.error("%s | error saving files: %s", name, e)

    # ✅ MANTIENI TUTTO LO STATO E AGGIORNA SOLO I CAMPI NECESSARI
    new_state = {
        **state,  # Mantieni tutto lo stato esistente
        "status": "ok",          
        "error_message": None,
        "refined_domain": dom_new,
        "refined_problem": prob_new,
        "messages": [],  # Pulisci solo i messaggi per evitare loop
    }
    
    _log_node_end(name, extra="UI edit received, continuing pipeline")
    return cast(PipelineState, new_state)


def node_template_fallback(state: PipelineState) -> PipelineState:
    name = "TemplateFallback"
    _log_node_start(name, state)

    LORE_SWITCH = {
        "example_lore"      : "examples/hero_lore_spec.json",
        "example_lore_copy" : "examples/hero_lore_spec.json",
        "default"           : "json_specs/generic.json"
    }

    lore_id = state["lore"].get("id", "default")
    json_path = Path(LORE_SWITCH.get(lore_id, LORE_SWITCH["default"]))
    spec = json.loads(json_path.read_text(encoding="utf-8"))

    env = Environment(trim_blocks=True, lstrip_blocks=True)
    DOMAIN_TEMPLATE  = env.from_string(domain_template_str)
    PROBLEM_TEMPLATE = env.from_string(problem_template_str)

    dom_pddl = DOMAIN_TEMPLATE.render(domain=spec["domain"])
    prob_pddl= PROBLEM_TEMPLATE.render(problem=spec["problem"])

    tmp = state.get("tmp_dir") or ""
    save_text_file(os.path.join(tmp, "domain_fallback.pddl"),  dom_pddl)
    save_text_file(os.path.join(tmp, "problem_fallback.pddl"), prob_pddl)

    new_state = {
        **state,
        "domain":  dom_pddl,
        "problem": prob_pddl,
        "status":  "ok",           # prosegue → Validate
        "error_message": None
    }
    _log_node_end(name, extra="PDDL built from template")
    return cast(PipelineState, new_state)

def node_generate_plan(state: PipelineState) -> PipelineState:
    """
    Runs Fast-Downward on the (refined) domain/problem and
    attaches the plan and log back into state.
    """
    print("\n=== Enter GeneratePlan_node ===")
    dom = state.get("refined_domain") or state.get("domain") or ""
    prob = state.get("refined_problem") or state.get("problem") or ""
    
    if dom == None or dom == "(define (domain ...))":
            dom = state.get("domain") or ""
    
    if prob == None or prob == "(define (problem ...))":
        prob = state.get("problem") or ""

    # guard in case something is missing
    if not dom or not prob:
        return { **state,
                 "status": "failed",
                 "error_message": "Missing domain or problem for planning" }

    # call your Fast-Downward wrapper
    result = generate_plan_with_fd(dom, prob)
    if result.get("found_plan"):
        print(f"\n{result["plan"]}\n")
        print("=== Exit GeneratePlan_node ===\n")
        return {
            **state,
            "plan":     result["plan"],
            "plan_log": result["log"],
            "status":   "ok",
            "error_message": None
        }
    else:
        print("Nessun piano trovato...")
        print("=== Exit GeneratePlan_node ===\n")
        return {
            **state,
            "plan":     None,
            "plan_log": result["log"],
            "status":   "failed",
            "error_message": "Planning failed"
        }

def end_node(state: PipelineState) -> PipelineState:
    print("\n=== Enter end_node ===")
    print(f"Stato finale: attempt={state.get('attempt')}, status={state.get('status')}")

    saver = cast(Any, state.get("__saver__"))

    if saver:
        if hasattr(saver, "delete_all"):
            saver.delete_all()
        else:
            conn = cast(Any, saver)._conn
            conn.execute("DELETE FROM checkpoints")
            conn.commit()

    minimal_state = cast(PipelineState, {
        "thread_id": state.get("thread_id", ""),
        "lore"     : state.get("lore", {}),
        "status"   : "done",
        "attempt"  : state.get("attempt", 0),
        "plan"     : state.get("plan"),
        "plan_log" : state.get("plan_log"),
    })

    print("=== Exit end_node ===\n")
    return minimal_state

# build_pipeline --------------------------------------------------

def build_pipeline(checkpointer=None):
    builder = StateGraph(PipelineState)

    # Starting point
    builder.add_node("Router", node_router)

    # Build‑Prompt chain
    builder.add_node("PreparePrompt", node_prepare_prompt)
    builder.add_node("GenerateVision", node_generate_vision)
    builder.add_node("GenerateSpec", node_generate_spec)

    # Core nodes
    builder.add_node("Generate", node_generate_pddl)
    builder.add_node("Validate", node_validate)
    builder.add_node("Refine", node_refine)
    builder.add_node("ChatFeedback", node_chat_feedback)
    builder.add_node("TemplateFallback", node_template_fallback)
    builder.add_node("GeneratePlan", node_generate_plan)
    builder.add_node("End", end_node)

    # Edges
    builder.set_entry_point("Router")
    builder.add_edge("PreparePrompt", "GenerateVision")
    builder.add_edge("GenerateVision", "GenerateSpec")
    builder.add_edge("GenerateSpec", "Generate")
    builder.add_edge("Generate", "Validate")

    builder.add_conditional_edges("Validate", path=validate_decision)
    builder.add_edge("Refine", "Validate")
    builder.add_conditional_edges("ChatFeedback", path=feedback_branch)
    builder.add_edge("TemplateFallback", "Validate")
    builder.add_edge("GeneratePlan", "End")
    builder.add_conditional_edges("GeneratePlan", path=plan_branch)

    builder.add_conditional_edges(
        "Router",
        lambda state: state["next_node"],
        {
            "PreparePrompt": "PreparePrompt",
            "Validate": "Validate"
        }
    )


    return builder.compile(checkpointer=checkpointer)



# Resto (get_pipeline_with_memory) invariato ------------------------------------

def get_pipeline_with_memory(thread_id: str, reset: bool = True):
    db = f"memory/{thread_id}.sqlite"
    os.makedirs(os.path.dirname(db), exist_ok=True)
    if reset and os.path.exists(db):
        os.remove(db)
    conn = sqlite3.connect(db, check_same_thread=False)
    saver = SqliteSaver(conn)
    logger.info("Pipeline with memory initialized (thread_id=%s)", thread_id)
    logger.info("")
    return build_pipeline(checkpointer=saver).with_config(configurable={"thread_id": thread_id})
