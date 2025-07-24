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
from datetime import datetime


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
    edited_domain: Annotated[Optional[str], non_empty_or_last]
    edited_problem: Annotated[Optional[str], non_empty_or_last]

    validation: Annotated[Optional[dict], last]
    error_message: Annotated[Optional[str], last]
    status: Annotated[Optional[str], last]

    attempt: Annotated[int, last]
    messages: Annotated[list[BaseMessage], last]#messages: Annotated[list[dict[str, str]], last]

    plan: Annotated[Optional[str], last]
    plan_log: Annotated[Optional[str], last]
    plan_url: Optional[str]
    config: Annotated[Dict[str, Any], last]
    found_plan: Annotated[Optional[bool], last]
    source: Annotated[Optional[str], last]

    _waiting_for_edit: Annotated[Optional[bool], last]
    _resume_after_feedback: Annotated[Optional[bool], last]
    _pipeline_completed: Annotated[Optional[bool], last]



# ────────────────────────────────────────────────────────────────────────────────
#  Helpers
# ────────────────────────────────────────────────────────────────────────────────
MAX_REFINE_ATTEMPTS = 2


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
    Router con priorità chiare e deterministiche per la ripresa della pipeline.
    
    PRIORITÀ (dall'alta alla bassa):
    1. Gestione attesa feedback utente
    2. Ripresa dopo feedback ricevuto  
    3. Ripresa normale con PDDL esistenti (SOLO se esplicitamente richiesta)
    4. Inizio standard della pipeline
    """
    _log_node_start("Router", state)

    # ──────────────────────────────────────────────────────────────────────
    # CONTROLLO PRELIMINARE: Pipeline già completata
    # ──────────────────────────────────────────────────────────────────────    
    if state.get("_pipeline_completed"):
        logger.info("🛑 [Router] Pipeline già completata, rimango in EndNode")
        _log_node_end("Router", "PIPELINE_COMPLETED")
        return {"next_node": "End", "status": state.get("status", "completed")}
        
    # ──────────────────────────────────────────────────────────────────────
    # CONTROLLO PRELIMINARE: Reset esplicito richiesto
    # ──────────────────────────────────────────────────────────────────────
    explicit_reset = state.get("_explicit_reset", False)
    if explicit_reset:
        logger.info("🔄 [Router] Reset esplicito richiesto, → PreparePrompt")
        result = {
            "next_node": "PreparePrompt",
            "status": "ok",
            "_explicit_reset": False,  # Reset del flag
            **reset_pipeline_state(state)
        }
        _log_node_end("Router", "EXPLICIT RESET")
        return result
    
    # ──────────────────────────────────────────────────────────────────────
    # PRIORITÀ 1: Siamo in attesa di feedback dall'utente
    # ──────────────────────────────────────────────────────────────────────
    if state.get("_waiting_for_edit"):
        logger.info("➡️ [Router] PRIORITÀ 1: In attesa di feedback, → ChatFeedback")
        result = {
            "next_node": "ChatFeedback",
            "status": "awaiting_feedback"  # Mantieni stato di attesa
        }
        _log_node_end("Router", "P1: waiting for edit")
        return result
    
    # ──────────────────────────────────────────────────────────────────────
    # PRIORITÀ 2: Abbiamo ricevuto feedback, riprendere validazione
    # ──────────────────────────────────────────────────────────────────────
    if state.get("_resume_after_feedback"):
        logger.info("➡️ [Router] PRIORITÀ 2: Feedback ricevuto, → Validate")
        
        # Assicura che i file PDDL siano salvati - con controllo robusto
        try:
            ensure_pddl_files_saved(state)
        except Exception as e:
            logger.error("❌ [Router] P2: Errore salvataggio PDDL: %s", e)
            # Se fallisce il salvataggio, ripartiamo da capo
            logger.info("🔄 [Router] P2: Riavvio pipeline da zero")
            result = {
                "next_node": "PreparePrompt",
                "status": "ok",
                "_resume_after_feedback": False
            }
            _log_node_end("Router", "P2: fallback to restart")
            return result
        
        result = {
            "next_node": "Validate",
            "status": "ok",
            "_resume_after_feedback": False  # Reset del flag
        }
        _log_node_end("Router", "P2: resume after feedback")
        return result
    
    # ──────────────────────────────────────────────────────────────────────
    # PRIORITÀ 3: Stato di attesa feedback (backward compatibility)
    # ──────────────────────────────────────────────────────────────────────
    if state.get("status") == "awaiting_feedback":
        logger.info("➡️ [Router] PRIORITÀ 3: Status awaiting_feedback, → ChatFeedback")
        result = {
            "next_node": "ChatFeedback",
            "status": "awaiting_feedback",
            "_waiting_for_edit": True  # Normalizza lo stato
        }
        _log_node_end("Router", "P3: backward compatibility")
        return result
    
    # ──────────────────────────────────────────────────────────────────────
    # PRIORITÀ 4: Ripresa normale con PDDL esistenti (SOLO se è una vera ripresa)
    # ──────────────────────────────────────────────────────────────────────
    if has_valid_pddl_state(state) and is_valid_resume_context(state):
        logger.info("➡️ [Router] PRIORITÀ 4: PDDL esistenti in contesto di ripresa valido")
        
        # NUOVO: Verifica che i file esistano effettivamente e siano validi
        try:
            # Prova a salvare/verificare i file PDDL
            ensure_pddl_files_saved(state)
            
            # Verifica che i file siano stati creati correttamente
            tmp_dir = state.get("tmp_dir")
            if tmp_dir:
                domain_path = os.path.join(tmp_dir, "domain.pddl")
                problem_path = os.path.join(tmp_dir, "problem.pddl")
                
                if os.path.exists(domain_path) and os.path.exists(problem_path):
                    logger.info("✅ [Router] P4: File PDDL verificati, → Validate")
                    result = {
                        "next_node": "Validate",
                        "status": "ok"
                    }
                    _log_node_end("Router", "P4: existing PDDL validated")
                    return result
                else:
                    logger.warning("⚠️ [Router] P4: File PDDL mancanti dopo salvataggio")
                    raise FileNotFoundError("File PDDL non trovati dopo salvataggio")
            else:
                logger.warning("⚠️ [Router] P4: tmp_dir non disponibile")
                raise ValueError("tmp_dir non disponibile nello stato")
                
        except Exception as e:
            logger.error("❌ [Router] P4: Errore verifica PDDL esistenti: %s", e)
            logger.info("🔄 [Router] P4: PDDL corrotti, riavvio pipeline da zero")
            
            # Pulisci stato corrotto e riparte da capo
            result = {
                "next_node": "PreparePrompt",
                "status": "ok",
                **reset_pipeline_state(state)
            }
            _log_node_end("Router", "P4: fallback to restart due to corruption")
            return result
    
    # ──────────────────────────────────────────────────────────────────────
    # PRIORITÀ 4B: PDDL presenti ma NON è una ripresa valida → RESET
    # ──────────────────────────────────────────────────────────────────────
    if has_valid_pddl_state(state) and not is_valid_resume_context(state):
        logger.info("🔄 [Router] PRIORITÀ 4B: PDDL presenti ma contesto non valido, reset automatico")
        result = {
            "next_node": "PreparePrompt", 
            "status": "ok",
            **reset_pipeline_state(state)
        }
        _log_node_end("Router", "P4B: auto reset - invalid resume context")
        return result
    
    # ──────────────────────────────────────────────────────────────────────
    # PRIORITÀ 5: Inizio standard della pipeline
    # ──────────────────────────────────────────────────────────────────────
    logger.info("➡️ [Router] PRIORITÀ 5: Inizio standard, → PreparePrompt")
    result = {
        "next_node": "PreparePrompt",
        "status": "ok"
    }
    _log_node_end("Router", "P5: standard start")
    return result

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
    raw = ask_ollama(template.replace("{{STORY}}", lore_txt), "llama3.2-vision")#raw = ask_ollama(template.replace("{{STORY}}", lore_txt))

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
    raw_out = ask_ollama(spec_prompt, "deepseek-coder-v2:16b") #raw_out = ask_ollama(spec_prompt)

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

        response = ask_ollama(prompt=final_prompt, model="devstral:24b") #response = ask_ollama(prompt=final_prompt)
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
    """Validazione con gestione corretta dei PDDL dopo feedback utente."""
    name = "Validate"
    _log_node_start(name, state)
    
    if state.get("status") != "ok":
        logger.warning("%s | skipped (status=%s)", name, state.get("status"))
        return {**state, "status": "failed", "error_message": "Skipped validate"}

    # Directory base dei file temporanei
    tmp_dir = state.get("tmp_dir") or ""
    edited_dir = os.path.join(tmp_dir, "edited")
    
    # Stato interno e tentativi
    attempt = state.get("attempt", -1)
    resume_feedback = state.get("_resume_after_feedback", False)
    
    # Variabili per PDDL da validare
    domain_to_validate = None
    problem_to_validate = None
    source_description = ""

    # 1) PRIORITÀ 1: PDDL editati dall'utente (sempre prioritari se presenti)
    if edited_dir and os.path.isdir(edited_dir):
        dom_path = os.path.join(edited_dir, "domain.pddl")
        prob_path = os.path.join(edited_dir, "problem.pddl")
        if os.path.exists(dom_path) and os.path.exists(prob_path):
            with open(dom_path, "r", encoding="utf-8") as f:
                domain_to_validate = f.read().strip()
            with open(prob_path, "r", encoding="utf-8") as f:
                problem_to_validate = f.read().strip()
            source_description = "edited files from disk"
            logger.info("%s | Using edited PDDL from %s", name, edited_dir)
    
    # 2) PRIORITÀ 2: PDDL dallo stato LangGraph (aggiornati da apply_user_feedback)
    if not domain_to_validate or not problem_to_validate:
        if resume_feedback or state.get("_waiting_for_edit") == False:
            # Dopo feedback, usa domain/problem aggiornati nello stato
            domain_to_validate = state.get("domain", "")
            problem_to_validate = state.get("problem", "")
            source_description = "state after feedback"
            logger.info("%s | Using domain/problem from state after feedback", name)
        elif attempt < 0:
            # Primo tentativo - usa PDDL originali
            domain_to_validate = state.get("domain", "")
            problem_to_validate = state.get("problem", "")
            source_description = "original generated"
            attempt = 0
        else:
            # Tentativi successivi - usa refined se disponibili, altrimenti originali
            domain_to_validate = state.get("refined_domain") or state.get("domain", "")
            problem_to_validate = state.get("refined_problem") or state.get("problem", "")
            source_description = "refined or original"
    
    # 3) Validazione dei PDDL ottenuti
    if not domain_to_validate or not problem_to_validate:
        error_msg = f"PDDL mancanti per la validazione (source: {source_description})"
        logger.error("%s | %s", name, error_msg)
        _log_node_end(name, "ERROR: missing PDDL")
        return cast(PipelineState, {
            **state,
            "status": "failed",
            "error_message": error_msg
        })
    
    logger.info("%s | Validating PDDL (attempt=%d, source=%s, domain=%d chars, problem=%d chars)", 
               name, attempt, source_description, len(domain_to_validate), len(problem_to_validate))
    
    try:
        # DEBUG: Log dei PDDL che stiamo validando
        print(f"\n=== VALIDATING PDDL (source: {source_description}) ===")
        print(f"Domain preview: {domain_to_validate}{'...' if len(domain_to_validate) > 200 else ''}")
        print(f"Problem preview: {problem_to_validate}{'...' if len(problem_to_validate) > 200 else ''}")
        print("=" * 50)
        
        validation = validate_pddl(domain_to_validate, problem_to_validate, state["lore"])
        valid_syntax = validation.get("valid_syntax", False)
        semantic_errors = validation.get("semantic_errors", [])
        
        if valid_syntax and not semantic_errors:
            status, error = "ok", None
            logger.info("%s | ✅ Validazione OK (source: %s)", name, source_description)
        else:
            status, error = "failed", "Validation errors found"
            logger.warning("%s | ❌ Validazione FAILED (source: %s)", name, source_description)
            logger.warning("%s | Syntax valid: %s, Semantic errors: %d", 
                          name, valid_syntax, len(semantic_errors))
        
    except Exception as e:
        logger.exception("%s | Errore durante validazione", name)
        validation = {"valid_syntax": False, "error": str(e)}
        status, error = "failed", f"Validation exception: {e}"
    
    # 4) Aggiorna lo stato con i risultati
    final_state = {
        **state,
        "validation": validation,
        "status": status,
        "error_message": error,
        "attempt": attempt,
        "_resume_after_feedback": False,  # Reset del flag
        # Conserva i PDDL editati nello stato se li abbiamo caricati da disco
        **({"edited_domain": domain_to_validate, "edited_problem": problem_to_validate} 
           if source_description == "edited files from disk" else {})
    }
    
    _log_node_end(name, f"status={status}, source={source_description}")
    return cast(PipelineState, final_state)


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
    
    current_lore_wrapper = state["lore"]

    print(f"[DBG][validate_decision] current_lore:\n {current_lore_wrapper}")
    
    # Estrai il JSON dalla chiave "text"
    try:
        current_lore_json = json.loads(current_lore_wrapper["text"])
    except (KeyError, json.JSONDecodeError):
        return "ChatFeedback"  # Se non riesce a parsare, vai a ChatFeedback
    
    # Lista dei file delle lore predefinite
    predefined_lore_files = [
        "lore/hero_lore.json",
        "lore/hacker_lore.json", 
        "lore/robot_lore.json"
    ]
    
    # Controlla se la lore corrente corrisponde a una di quelle predefinite
    for lore_file in predefined_lore_files:
        try:
            with open(lore_file, 'r', encoding='utf-8') as f:
                predefined_lore = json.load(f)
            if current_lore_json == predefined_lore:
                return "TemplateFallback"
        except (FileNotFoundError, json.JSONDecodeError):
            continue
    
    # Se non corrisponde a nessuna lore predefinita
    return "ChatFeedback"

def feedback_branch(state: PipelineState) -> Optional[str]:
    """
    Determina il prossimo nodo dopo ChatFeedback.
    
    Returns:
        None: rimane in ChatFeedback (ancora in attesa)
        "Validate": procede con la validazione
    """
    # Se stiamo ancora aspettando feedback, rimani nel nodo
    if state.get("_waiting_for_edit"):
        logger.debug("FeedbackBranch | ancora in attesa di edit")
        return None
    
    # Se il feedback è stato processato, vai alla validazione
    if state.get("_resume_after_feedback") or state.get("status") == "ok":
        logger.debug("FeedbackBranch | feedback processato → Validate")
        return "Validate"
    
    # Fallback sicuro
    logger.warning("FeedbackBranch | stato inatteso, → Validate")
    return "Validate"

def plan_branch(state: PipelineState) -> str:
    if state.get("status") != "failed":
        return "End"
    
    current_lore_wrapper = state["lore"]
    
    try:
        current_lore_json = json.loads(current_lore_wrapper["text"])
    except (KeyError, json.JSONDecodeError):
        return "ChatFeedback"  # Se non riesce a parsare, vai a ChatFeedback
    
    predefined_lore_files = [
        "lore/hero_lore.json",
        "lore/hacker_lore.json", 
        "lore/robot_lore.json"
    ]
    
    for lore_file in predefined_lore_files:
        try:
            with open(lore_file, 'r', encoding='utf-8') as f:
                predefined_lore = json.load(f)
            if current_lore_json == predefined_lore:
                return "TemplateFallback"
        except (FileNotFoundError, json.JSONDecodeError):
            continue
    
    return "ChatFeedback"

# ────────────────────────────────────────────────────────────────────
#  Nodo ChatFeedback – blocca il grafo finché l’utente non risponde
# ────────────────────────────────────────────────────────────────────
def node_chat_feedback(state: PipelineState) -> PipelineState | Interrupt:
    """
    Gestione feedback utente con stato pulito e ripresa garantita.
    
    FLUSSO:
    1. Prima chiamata: invia PDDL al frontend e interrompe
    2. Chiamate successive: attende modifiche utente
    3. Modifiche ricevute: prepara ripresa verso Validate
    """
    name = "ChatFeedback"
    _log_node_start(name, state)

    # FASE 1: Prima chiamata - Invia PDDL al frontend
    if not state.get("_waiting_for_edit"):
        logger.info("%s | FASE 1: Invio PDDL al frontend per modifica", name)
        
        domain = state.get("refined_domain") or state.get("domain") or ""
        problem = state.get("refined_problem") or state.get("problem") or ""
        
        if not domain or not problem:
            error_msg = "Impossibile inviare PDDL vuoti al frontend"
            logger.error("%s | %s", name, error_msg)
            _log_node_end(name, "ERROR: empty PDDL")
            return cast(PipelineState, {
                **state,
                "status": "failed",
                "error_message": error_msg
            })
        
        new_state = {
            **state,
            "status": "awaiting_feedback",
            "_waiting_for_edit": True,
            "_resume_after_feedback": False,
            "domain": domain,
            "problem": problem,
            "error_message": None
        }

        state["status"] = "awaiting_feedback"
        state["_waiting_for_edit"] = True
        state["_resume_after_feedback"] = False
        state["domain"] = domain
        state["problem"] = problem
        state["error_message"] = None
        
        payload = {
            "domain": domain,
            "problem": problem,
            "message": "Modifica i file PDDL e invia quando pronto"
        }
        
        _log_node_end(name, "INTERRUPT: waiting for user edit")
        return interrupt(payload)
    
    # FASE 2: In attesa - Controlla messaggi utente
    messages = state.get("messages", [])
    latest_user_message = None
    
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            latest_user_message = msg
            break
    
    print(f"[DBG][chat_feedback] FASE 2: latest_user_message found: {latest_user_message is not None}")
    
    if not latest_user_message:
        logger.info("%s | FASE 2: Ancora in attesa di modifiche utente", name)
        _log_node_end(name, "still waiting")
        return cast(PipelineState, state)  # ✅ Mantieni stato completo
    
    # FASE 3: Modifiche ricevute - Parsing e validazione
    try:
        # --- INIZIO DEBUG PRINTS ---
        raw_content = str(latest_user_message.content)
        print("[DBG][chat_feedback] Raw human message content:", repr(raw_content))

        payload = json.loads(raw_content)
        print("[DBG][chat_feedback] Parsed payload keys:", list(payload.keys()))

        new_domain  = (payload.get("domain")  or "").strip()
        new_problem = (payload.get("problem") or "").strip()

        print("[DBG][chat_feedback] domain length:", len(new_domain),
              "| problem length:", len(new_problem))
        print("[DBG][chat_feedback] domain preview:",
              (new_domain[:120] + ("..." if len(new_domain) > 120 else "")))
        print("[DBG][chat_feedback] problem preview:",
              (new_problem[:120] + ("..." if len(new_problem) > 120 else "")))

        if not new_domain or not new_problem:
            print("[DBG][chat_feedback] Payload incompleto. domain vuoto?", not new_domain,
                  "problem vuoto?", not new_problem)
            _log_node_end(name, "incomplete payload")
            return cast(PipelineState, state)
        # --- FINE DEBUG PRINTS ---

        logger.info("%s | FASE 3: Modifiche ricevute (domain: %d chars, problem: %d chars)", 
                     name, len(new_domain), len(new_problem))
        
        logger.debug("%s | Domain preview: %s...", name, new_domain[:100])
        logger.debug("%s | Problem preview: %s...", name, new_problem[:100])
        
    except (json.JSONDecodeError, KeyError, AttributeError) as e:
        error_msg = f"Errore parsing payload: {e}"
        logger.error("%s | %s", name, error_msg)
        _log_node_end(name, f"parse error: {e}")
        return cast(PipelineState, state)
    
    # FASE 4: Salvataggio modifiche e preparazione ripresa
    tmp_dir = state.get("tmp_dir")
    if tmp_dir:
        edited_dir = os.path.join(tmp_dir, "edited")
        os.makedirs(edited_dir, exist_ok=True)
        try:
            save_text_file(os.path.join(edited_dir, "domain_user_edit.pddl"), new_domain)
            save_text_file(os.path.join(edited_dir, "problem_user_edit.pddl"), new_problem)
            logger.info("%s | File modificati salvati in edited_dir", name)
        except Exception as e:
            logger.error("%s | Errore salvataggio file: %s", name, e)
    
    # FASE 5: Stato finale per la ripresa
    final_state = {
        **state,
        "_waiting_for_edit": False,
        "_resume_after_feedback": True,
        "refined_domain": new_domain,
        "refined_problem": new_problem,
        "status": "ok",
        "error_message": None,
        "messages": []
    }
    
    logger.info("%s | FASE 5: Preparazione completata per ripresa → Validate", name)
    _log_node_end(name, "resume prepared")

    # DEBUG finale prima del return
    print("[DBG][chat_feedback] Edit valido: pronto a resume. domain hash:",
    __import__("hashlib").sha256(new_domain.encode()).hexdigest()[:8], 
    "problem hash:", __import__("hashlib").sha256(new_problem.encode()).hexdigest()[:8])

    return cast(PipelineState, final_state)


def node_template_fallback(state: PipelineState) -> PipelineState:
    name = "TemplateFallback"
    _log_node_start(name, state)

    # Mapping tra file lore e corrispondenti spec
    LORE_TO_SPEC = {
        "lore/hero_lore.json": "examples/hero_lore.json",
        "lore/hacker_lore.json": "examples/hacker_lore.json",
        "lore/robot_lore.json": "examples/robot_lore.json"
    }

    # Estrai il JSON dalla lore corrente
    current_lore_wrapper = state["lore"]
    try:
        current_lore_json = json.loads(current_lore_wrapper["text"])
    except (KeyError, json.JSONDecodeError):
        json_path = Path("json_specs/generic.json")
        spec = json.loads(json_path.read_text(encoding="utf-8"))
    else:
        # Trova quale lore corrisponde a quella corrente
        spec_path = None
        for lore_file, spec_file in LORE_TO_SPEC.items():
            try:
                with open(lore_file, 'r', encoding='utf-8') as f:
                    predefined_lore = json.load(f)
                if current_lore_json == predefined_lore:
                    spec_path = spec_file
                    break
            except (FileNotFoundError, json.JSONDecodeError):
                continue
        
        # Carica la spec corrispondente o fallback di default
        if spec_path:
            json_path = Path(spec_path)
        else:
            json_path = Path("json_specs/generic.json")
        
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
        "status":  "ok",
        "error_message": None,
        "refined_domain": dom_pddl,
        "refined_problem": prob_pddl
    }
    _log_node_end(name, extra="PDDL built from template")
    return cast(PipelineState, new_state)

def node_generate_plan(state: PipelineState) -> PipelineState:
    """
    Genera un piano utilizzando Fast-Downward sui PDDL validati.
    Usa la stessa logica di prioritizzazione della validazione.
    """
    name = "GeneratePlan"
    print(f"\n=== Enter {name}_node ===")
    
    # Directory base dei file temporanei
    tmp_dir = state.get("tmp_dir") or ""
    edited_dir = os.path.join(tmp_dir, "edited")
    
    # Stato interno e tentativi
    resume_feedback = state.get("_resume_after_feedback", False)
    attempt = state.get("attempt", -1)
    
    # Variabili per PDDL da usare per planning
    domain_for_planning = None
    problem_for_planning = None
    source_description = ""

    # 1) PRIORITÀ 1: PDDL editati dall'utente (sempre prioritari se presenti)
    if edited_dir and os.path.isdir(edited_dir):
        dom_path = os.path.join(edited_dir, "domain.pddl")
        prob_path = os.path.join(edited_dir, "problem.pddl")
        if os.path.exists(dom_path) and os.path.exists(prob_path):
            with open(dom_path, "r", encoding="utf-8") as f:
                domain_for_planning = f.read().strip()
            with open(prob_path, "r", encoding="utf-8") as f:
                problem_for_planning = f.read().strip()
            source_description = "edited files from disk"
            logger.info("%s | Using edited PDDL from %s", name, edited_dir)
    
    # 2) PRIORITÀ 2: PDDL dallo stato LangGraph (aggiornati da feedback)
    if not domain_for_planning or not problem_for_planning:
        if resume_feedback or state.get("_waiting_for_edit") == False:
            # Dopo feedback, usa domain/problem aggiornati nello stato
            domain_for_planning = state.get("domain", "")
            problem_for_planning = state.get("problem", "")
            source_description = "state after feedback"
            logger.info("%s | Using domain/problem from state after feedback", name)
        else:
            # Usa refined se disponibili, altrimenti originali
            domain_for_planning = state.get("refined_domain") or state.get("domain", "")
            problem_for_planning = state.get("refined_problem") or state.get("problem", "")
            source_description = "refined or original"
    
    # 3) Fallback per gestire casi edge
    if not domain_for_planning or domain_for_planning in [None, "(define (domain ...)))"]:
        domain_for_planning = state.get("domain", "")
    
    if not problem_for_planning or problem_for_planning in [None, "(define (problem ...)))"]:
        problem_for_planning = state.get("problem", "")
    
    # 4) Validazione finale
    if not domain_for_planning or not problem_for_planning:
        error_msg = f"Missing domain or problem for planning (source: {source_description})"
        logger.error("%s | %s", name, error_msg)
        print(f"❌ {error_msg}")
        print(f"=== Exit {name}_node ===\n")
        
        # Emetti errore al frontend
        emit_sse_event("GeneratePlan", {
            "status": "failed",
            "error": error_msg,
            "source": source_description
        }, state)
        
        return {
            **state,
            "status": "failed",
            "error_message": error_msg
        }

    print(f"📋 Planning with PDDL from: {source_description}")
    print(f"   Domain: {len(domain_for_planning)} chars")
    print(f"   Problem: {len(problem_for_planning)} chars")
    
    # 5) Genera il piano
    try:
        result = generate_plan_with_fd(domain_for_planning, problem_for_planning)
        
        if result.get("found_plan"):
            plan_text = result["plan"]
            plan_log = result["log"]
            
            print(f"✅ Piano trovato!")
            print(f"\n{plan_text}\n")
            
            # 6) Salva il piano su file (opzionale)
            plan_url = None
            if tmp_dir:
                try:
                    plan_file = os.path.join(tmp_dir, "plan.txt")
                    with open(plan_file, "w", encoding="utf-8") as f:
                        f.write(f"=== PIANO GENERATO ===\n\n")
                        f.write(f"Source: {source_description}\n")
                        f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
                        f.write(f"=== PLAN ===\n{plan_text}\n\n")
                        f.write(f"=== LOG ===\n{plan_log}")
                    
                    # Genera URL per download se hai una funzione disponibile
                    # plan_url = generate_file_url(plan_file, "plan.txt")  # Sostituisci con la tua funzione
                    plan_url = f"/tmp/files/{os.path.basename(plan_file)}"  # URL semplificato
                    logger.info("%s | Piano salvato in %s", name, plan_file)
                except Exception as e:
                    logger.warning("%s | Impossibile salvare piano su file: %s", name, e)
            
            # 7) Emetti evento SSE al frontend
            # emit_sse_event("GeneratePlan", {
            #     "status": "success",
            #     "plan": plan_text,
            #     "plan_log": plan_log,
            #     "source": source_description,
            #     "plan_url": plan_url,
            #     "found_plan": True,
            #     "domain_chars": len(domain_for_planning),
            #     "problem_chars": len(problem_for_planning),
            #     #"_pipeline_completed": True
            # }, state)
            logger.info(f"✅ [GeneratePlan_node] Evento GeneratePlan emesso e pipeline continua.")
            
            print(f"=== Exit {name}_node ===\n")
            return {
                **state,
                "plan": plan_text,
                "plan_log": plan_log,
                "plan_url": plan_url,  
                "status": "success",
                "error_message": None,
                "found_plan": True,
                "source": source_description
            }
        else:
            print("❌ Nessun piano trovato...")
            
            # Emetti fallimento al frontend
            emit_sse_event("GeneratePlan", {
                "status": "failed", 
                "found_plan": False,
                "plan_log": result["log"],
                "source": source_description,
                "error": "No plan found by Fast-Downward"
            }, state)
            
            print(f"=== Exit {name}_node ===\n")
            return {
                **state,
                "plan": None,
                "plan_log": result["log"],
                "status": "failed",
                "error_message": "Planning failed"
            }
    
    except Exception as e:
        logger.exception("%s | Errore durante planning", name)
        error_msg = f"Planning exception: {e}"
        print(f"❌ {error_msg}")
        
        # # Emetti eccezione al frontend
        # emit_sse_event("GeneratePlan", {
        #     "status": "error",
        #     "error": error_msg,
        #     "source": source_description,
        #     "exception": str(e)
        # }, state)
        
        print(f"=== Exit {name}_node ===\n")
        return {
            **state,
            "plan": None,
            "plan_log": str(e),
            "status": "error",
            "error_message": error_msg
        }

def end_node(state: PipelineState) -> PipelineState:
    """
    Nodo finale che pulisce il database LangGraph per evitare che la pipeline 
    riparta da stati intermedi in esecuzioni successive.
    """
    name = "EndNode"
    thread_id = state.get("thread_id", "unknown")
    
    print(f"\n=== Enter {name} ===")
    print(f"Thread ID: {thread_id}")
    print(f"Stato finale: attempt={state.get('attempt')}, status={state.get('status')}")

    plan = state.get("plan")
    plan_url = state.get("plan_url")
    thread_id = state.get("thread_id")

    new_state: PipelineState = {
        **state,
        "status": "completed",
        "_pipeline_completed": True,
        "thread_id": thread_id,
        "plan": plan,
        "plan_url": plan_url,
        "status": state.get("status", "ok")
    }

    # emit_sse_event("PipelineCompleted", {
    #     "status": "completed",
    #     "_pipeline_completed": True,
    #     "thread_id": thread_id,
    #     "plan": plan,
    #     "plan_url": plan_url,
    # }, new_state)

    # 1) Pulisci il database LangGraph per questo thread
    try:
        saver = cast(Any, state.get("__saver__"))
        
        if saver:
            # Prova prima il metodo preferito
            if hasattr(saver, "delete_all"):
                saver.delete_all()
                logger.info("%s | ✅ Database LangGraph pulito via delete_all() per thread: %s", name, thread_id)
            else:
                # Fallback al metodo diretto
                conn = cast(Any, saver)._conn
                if conn:
                    conn.execute("DELETE FROM checkpoints")
                    conn.commit()
                    logger.info("%s | ✅ Database LangGraph pulito via SQL per thread: %s", name, thread_id)
                else:
                    logger.warning("%s | ⚠️ Connessione database non disponibile per thread: %s", name, thread_id)
        else:
            logger.warning("%s | ⚠️ Saver non disponibile per thread: %s", name, thread_id)
            
    except Exception as e:
        logger.error("%s | ❌ Errore pulizia database LangGraph per thread %s: %s", name, thread_id, e)
        # Non fermare l'esecuzione per errori di pulizia
    
    # 2) Pulisci anche i file temporanei se presenti
    # try:
    #     tmp_dir = state.get("tmp_dir")
    #     if tmp_dir and os.path.exists(tmp_dir):
    #         import shutil
    #         shutil.rmtree(tmp_dir)
    #         logger.info("%s | ✅ Directory temporanea rimossa: %s", name, tmp_dir)
    # except Exception as e:
    #     logger.warning("%s | ⚠️ Errore rimozione directory temporanea: %s", name, e)
    
    # 3) Stato finale minimale - conserva solo le informazioni essenziali
    final_status = state.get("status", "completed")
    if final_status not in ["ok", "failed", "done"]:
        final_status = "completed"
    
    minimal_state = cast(PipelineState, {
        "thread_id": thread_id,
        "lore": state.get("lore", {}),
        "status": final_status,
        "attempt": state.get("attempt", 0),
        "plan": state.get("plan"),
        "plan_log": state.get("plan_log"),
        "domain": state.get("refined_domain") or state.get("domain"),
        "problem": state.get("refined_problem") or state.get("problem"),
        "validation": state.get("validation"),
        "_pipeline_completed": True
    })
    
    logger.info("%s | 🏁 Pipeline completata per thread: %s, status: %s", 
                name, thread_id, final_status)
    print(f"🏁 Pipeline completata con status: {final_status}")
    print(f"=== Exit {name} ===\n")
    
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
            "Validate": "Validate",
            "ChatFeedback": "ChatFeedback",
            "End": "End"
        }
    )
    return builder.compile(checkpointer=checkpointer)


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


def has_valid_pddl_state(state: PipelineState) -> bool:
    """
    Verifica se lo stato contiene PDDL validi.
    
    Args:
        state: Stato della pipeline da verificare
        
    Returns:
        True se lo stato contiene PDDL validi, False altrimenti
    """
    domain = state.get("domain")
    problem = state.get("problem")
    
    # Controlli base di validità
    if not domain or not problem:
        return False
    
    # Verifica che non siano stringhe vuote
    if not str(domain).strip() or not str(problem).strip():
        return False
    
    # Verifica minima che sembrino PDDL validi
    domain_str = str(domain).strip()
    problem_str = str(problem).strip()
    
    # Controlli minimi di struttura PDDL
    if not (domain_str.startswith("(define") and domain_str.endswith(")")):
        logger.warning("⚠️ [has_valid_pddl_state] Domain non sembra PDDL valido")
        return False
    
    if not (problem_str.startswith("(define") and problem_str.endswith(")")):
        logger.warning("⚠️ [has_valid_pddl_state] Problem non sembra PDDL valido")
        return False
    
    return True


def is_valid_resume_context(state: PipelineState) -> bool:
    """
    Determina se il contesto attuale è valido per una ripresa della pipeline.
    
    Una ripresa è valida SOLO quando:
    1. Stiamo esplicitamente riprendendo dopo feedback utente, OPPURE  
    2. Stiamo in uno stato di attesa feedback, OPPURE
    3. Abbiamo indicatori espliciti di ripresa in corso
    
    Args:
        state: Stato della pipeline da verificare
        
    Returns:
        True se è un contesto di ripresa valido, False altrimenti
    """
    
    # Caso 1: Flags espliciti di ripresa
    if state.get("_resume_after_feedback"):
        logger.info("✅ [is_valid_resume_context] Resume dopo feedback")
        return True
        
    if state.get("_waiting_for_edit"):
        logger.info("✅ [is_valid_resume_context] In attesa di edit")
        return True
    
    # Caso 2: Status che indicano ripresa
    status = state.get("status", "")
    valid_resume_statuses = {
        "awaiting_feedback", 
        "processing_feedback",
        "validating",
        "refining"
    }
    
    if status in valid_resume_statuses:
        logger.info("✅ [is_valid_resume_context] Status valido per ripresa: %s", status)
        return True
    
    # Caso 3: Presenza di validazione in corso (indica processo avanzato)
    if state.get("validation") is not None:
        logger.info("✅ [is_valid_resume_context] Validazione presente, probabile ripresa")
        return True
    
    # Caso 4: Presenza di PDDL refinati (indica processo molto avanzato)
    if state.get("refined_domain") or state.get("refined_problem"):
        logger.info("✅ [is_valid_resume_context] PDDL refinati presenti, ripresa valida")
        return True
    
    # Caso 5: Messaggi recenti che indicano interazione utente
    messages = state.get("messages", [])
    if messages:
        # Controlla se ci sono messaggi recenti (ultimi 2)
        recent_messages = messages[-2:] if len(messages) >= 2 else messages
        
        for msg in recent_messages:
            if isinstance(msg, dict):
                msg_type = msg.get("type", "")
                content = str(msg.get("content", "")).lower()
                
                # Messaggi utente recenti indicano interazione in corso
                if msg_type == "human":
                    logger.info("✅ [is_valid_resume_context] Messaggio utente recente trovato")
                    return True
                    
                # Messaggi AI che parlano di feedback/editing
                if msg_type == "ai" and any(keyword in content for keyword in 
                                         ["edit", "modifica", "feedback", "correggi", "valida"]):
                    logger.info("✅ [is_valid_resume_context] Messaggio AI di feedback recente")
                    return True
    
    # Caso 6: Check temporale - se è passato poco tempo dalla creazione
    # (questo previene riprese spurie dopo molto tempo)
    tmp_dir = state.get("tmp_dir")
    if tmp_dir and os.path.exists(tmp_dir):
        try:
            import time
            dir_mtime = os.path.getmtime(tmp_dir)
            current_time = time.time()
            
            # Se la directory è stata modificata negli ultimi 30 minuti
            if (current_time - dir_mtime) < 1800:  # 30 minuti
                logger.info("✅ [is_valid_resume_context] tmp_dir recente, ripresa valida")
                return True
        except OSError:
            pass
    
    # Default: NON è una ripresa valida
    logger.info("❌ [is_valid_resume_context] Nessun indicatore di ripresa valido trovato")
    return False


def reset_pipeline_state(state: PipelineState) -> dict:
    """
    Reset completo dello stato della pipeline per riavvio pulito.
    
    Args:
        state: Stato corrente della pipeline
        
    Returns:
        Aggiornamenti da applicare allo stato per il reset
    """
    logger.info("🔄 [reset_pipeline_state] Reset completo dello stato")
    
    # Mantieni solo i dati essenziali
    thread_id = state.get("thread_id", "default")
    lore = state.get("lore", {})
    messages = state.get("messages", [])
    
    # Pulisci tmp_dir esistente se presente
    old_tmp_dir = state.get("tmp_dir")
    if old_tmp_dir and os.path.exists(old_tmp_dir):
        try:
            import shutil
            shutil.rmtree(old_tmp_dir)
            logger.info("🧹 [reset_pipeline_state] Rimossa tmp_dir: %s", old_tmp_dir)
        except Exception as e:
            logger.warning("⚠️ [reset_pipeline_state] Errore rimozione tmp_dir: %s", e)
    
    return {
        "domain": None,
        "problem": None,
        "refined_domain": None,
        "refined_problem": None,
        "validation": None,
        "tmp_dir": None,
        "_waiting_for_edit": False,
        "_resume_after_feedback": False,
        "status": "reset",        
        "thread_id": thread_id,
        "lore": lore,
        "messages": messages
    }

def ensure_pddl_files_saved(state: PipelineState) -> None:
    """
    Assicura che i file PDDL siano salvati su disco, con gestione robusta delle directory.
    
    Args:
        state: Stato della pipeline contenente domain, problem e tmp_dir
        
    Raises:
        ValueError: Se domain o problem sono mancanti nello stato
        OSError: Se non è possibile creare le directory o salvare i file
    """
    logger.info("💾 [ensure_pddl_files_saved] Inizio salvataggio PDDL")
    
    # Verifica che i dati PDDL siano disponibili nello stato
    domain = state.get("domain")
    problem = state.get("problem")
    
    if not domain or not problem:
        error_msg = f"PDDL mancanti nello stato - domain: {bool(domain)}, problem: {bool(problem)}"
        logger.error("❌ [ensure_pddl_files_saved] %s", error_msg)
        raise ValueError(error_msg)
    
    # Ottieni o crea tmp_dir
    tmp_dir = state.get("tmp_dir")
    if not tmp_dir:
        # Crea una nuova tmp_dir basata su thread_id
        thread_id = state.get("thread_id", "default")
        tmp_dir = os.path.join("static", "uploads", thread_id)
        logger.info("📁 [ensure_pddl_files_saved] Creata nuova tmp_dir: %s", tmp_dir)
        
        # Aggiorna lo stato con la nuova tmp_dir
        state["tmp_dir"] = tmp_dir
    
    # Assicura che la directory esista
    try:
        os.makedirs(tmp_dir, exist_ok=True)
        logger.info("✅ [ensure_pddl_files_saved] Directory creata/verificata: %s", tmp_dir)
    except OSError as e:
        error_msg = f"Impossibile creare directory {tmp_dir}: {e}"
        logger.error("❌ [ensure_pddl_files_saved] %s", error_msg)
        raise OSError(error_msg) from e
    
    # Salva i file PDDL
    domain_path = os.path.join(tmp_dir, "domain.pddl")
    problem_path = os.path.join(tmp_dir, "problem.pddl")
    
    try:
        # Salva domain.pddl
        with open(domain_path, "w", encoding="utf-8") as f:
            f.write(str(domain))
        logger.info("✅ [ensure_pddl_files_saved] Domain salvato: %s", domain_path)
        
        # Salva problem.pddl
        with open(problem_path, "w", encoding="utf-8") as f:
            f.write(str(problem))
        logger.info("✅ [ensure_pddl_files_saved] Problem salvato: %s", problem_path)
        
        # Verifica che i file siano stati creati correttamente
        if not os.path.exists(domain_path) or not os.path.exists(problem_path):
            raise OSError("File PDDL non trovati dopo il salvataggio")
        
        # Verifica che i file non siano vuoti
        if os.path.getsize(domain_path) == 0 or os.path.getsize(problem_path) == 0:
            raise OSError("File PDDL vuoti dopo il salvataggio")
        
        logger.info("✅ [ensure_pddl_files_saved] PDDL salvati e verificati con successo")
        
    except (OSError, IOError) as e:
        error_msg = f"Errore salvataggio file PDDL in {tmp_dir}: {e}"
        logger.error("❌ [ensure_pddl_files_saved] %s", error_msg)
        raise OSError(error_msg) from e


def emit_sse_event(event_type: str, data: dict, state: PipelineState):
    """
    Emette un evento SSE. Adatta questa funzione in base al tuo sistema.
    """
    # Esempio - sostituisci con la tua implementazione
    try:
        event_data = json.dumps(data)
        print(f"SSE_EVENT: {event_type} - {event_data}")
        # Se hai un sistema di eventi, usalo qui
        # es: your_sse_emitter.emit(event_type, data)
    except Exception as e:
        print(f"Errore nell'emissione evento SSE: {e}")