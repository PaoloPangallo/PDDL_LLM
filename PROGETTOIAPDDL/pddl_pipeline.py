import os
import json
import logging
import re
from typing import TypedDict, Optional, Any, Dict, List, Mapping, Tuple, Set
from jinja2 import Template, Environment
from types import SimpleNamespace

from langgraph.graph import StateGraph
from game.generator import build_prompt_from_lore, build_prompt_from_lore2
from game.utils import ask_ollama, extract_between, save_text_file, load_few_shot_examples
from game.validator import validate_pddl
from agent.reflection_agent import refine_pddl
from game.validator import generate_plan_with_fd
from db.db import retrieve_similar_examples_from_db
from game.utils import strip_pddl_artifacts, extract_section

# ---------------------
# Logging setup
# ---------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("PDDL_Pipeline")

# ---------------------
# Stato del flusso
# ---------------------
class PDDLState(TypedDict):
    lore: dict
    prompt: Optional[str]
    domain: Optional[str]
    problem: Optional[str]
    validation: Optional[dict]
    error_message: Optional[str]
    domain_backup: Optional[str]
    problem_backup: Optional[str]
    refined_domain: Optional[str]
    refined_problem: Optional[str]
    attempt: int

# ---------------------
# Nodi della pipeline
# ---------------------
def node_build_prompt(state: PDDLState) -> PDDLState:
    """Costruisce il prompt da fornire al LLM a partire dalla lore."""
    logger.info("🔧 BuildPrompt — costruzione del prompt\n")

    lore_raw = state["lore"]

    if isinstance(lore_raw, str):
        with open(lore_raw, encoding="utf-8") as f:
            lore = json.load(f)
    else:
        lore = lore_raw

    #logger.debug("BuildPrompt — lore keys: %s", list(lore.keys()))
    #logger.debug("BuildPrompt — lore:\n%s", json.dumps(lore, indent=2)[:400])

    logger.info("🧾 Lore ricevuta:\n %s", json.dumps(lore or {}, indent=2))

    logger.info("✅ Lore pronta all'uso.\n")

    few_shot_examples = load_few_shot_examples("examples", max_examples=3)
    prompt, *_ = build_prompt_from_lore2(lore, few_shot_examples)

    # print("\n")
    # logger.debug("BuildPrompt — prompt generato:\n%s\n", prompt)
    # print("\n")

    state["prompt"] = prompt
    state.setdefault("attempt", 0)

    logger.debug("📄 Prompt generato (primi 700 caratteri):\n%s...\n\n", prompt[:700])
    return state


def node_generate_pddl(state: PDDLState) -> dict:
    """Genera dominio e problema PDDL a partire dal prompt."""
    try:
        logger.debug("GeneratePDDL — invio a Ollama")
        prompt: str = state.get("prompt") or ""

        response = ask_ollama(prompt)

        print("\n")
        logger.debug("GeneratePDDL — risposta ricevuta:\n%s\n", response)

        #domain = extract_between(response, "=== DOMAIN START ===", "=== DOMAIN END ===")
        #problem = extract_between(response, "=== PROBLEM START ===", "=== PROBLEM END ===")

        domain = extract_section(response, "DOMAIN")
        problem = extract_section(response, "PROBLEM")

        if not domain or not problem:
            raise ValueError("Estrazione dominio o problema fallita")

        domain = strip_pddl_artifacts(domain)
        problem = strip_pddl_artifacts(problem)

        print("\n")
        print("Domain:\n", domain)
        print("\n")
        print("Problem:\n", problem)
        print("\n")

        state["domain_backup"]  = domain
        state["problem_backup"] = problem

        return {"domain": domain, "problem": problem, "error_message": None}
    except Exception as err:
        logger.error("GeneratePDDL — errore: %s", err, exc_info=True)
        return {"domain": None, "problem": None, "error_message": str(err)}


def node_validate(state: PDDLState) -> dict:
    """Valida i file PDDL usando il contenuto della lore."""
    logger.info("ValidatePDDL — Validazione in corso...\n")
    domain = state.get("domain")
    problem = state.get("problem")
    if not domain or not problem:
        msg = "Mancano dominio o problema per la validazione - si useranno quelli di backup"
        #logger.warning("Validate — %s", msg)
        #return {"validation": None, "error_message": msg}
        domain = state.get("domain_backup") or ""
        problem = state.get("problem_backup") or ""

    try:
        validation = validate_pddl(domain, problem, state["lore"])
        valid_syntax = validation.get("valid_syntax", False)
        raw_summary = validation.get("validation_summary", "")

        # Spezza in righe, ripulisci tabulazioni e filtra quelle da scartare
        summary_lines = []
        for line in raw_summary.splitlines():
            text = line.lstrip("\t")
            # Scarta la riga del comando translator o qualsiasi riga con percorsi /tmp/…
            if text.startswith("INFO") and "translator command line string" in text:
                continue
            if "/" in text and ("tmp" in text or "home" in text):
                continue
            if text.strip():
                summary_lines.append(text)

        # Costruisci l’output
        lines = [
            "🧠 Validation report:",
            f" - valid_syntax: {valid_syntax}",
            " - validation_summary:",
        ]
        lines += [f"    {l}" for l in summary_lines]

        # Logga in un unico messaggio
        logger.info("\n".join(lines))
        print("\n")

        # Controllo sintassi
        if not validation.get("valid_syntax", False):
            msg = "Sintassi PDDL non valida"
            logger.warning("Validate — %s\n", msg)
            return {"validation": validation, "error_message": msg}

        # Controlli semantici
        # issues = []
        # if validation.get("undefined_objects_in_goal"):
        #     count = len(validation["undefined_objects_in_goal"])
        #     issues.append(f"{count} oggetti non definiti nel goal")
        # if validation.get("undefined_actions"):
        #     count = len(validation["undefined_actions"])
        #     issues.append(f"{count} azioni non definite")
        # if validation.get("semantic_errors"):
        #     count = len(validation["semantic_errors"])
        #     issues.append(f"{count} errori semantici")
        # if issues:
        #     msg = "; ".join(issues)
        #     logger.warning("Validate — problemi semantici: %s", msg)
        #     return {"validation": validation, "error_message": msg}

        logger.info("Validate — PDDL valido sintatticamente e semanticamente")
        return {"validation": validation, "error_message": None}

    except Exception as err:
        msg = f"Errore durante la validazione: {err}"
        logger.error("Validate — %s", msg, exc_info=True)
        return {"validation": None, "error_message": msg}


def node_refine(state: PDDLState) -> dict:
    """Raffina i file PDDL in base agli errori emersi."""
    try:
        attempt = state.get("attempt", 0)
        logger.debug("Refine — Tentaivo %d — Avvio con error_message: %s\n", attempt + 1, state.get("error_message"))
        errorMessage: str = state.get("error_message") or ""

        refined = refine_pddl(
            domain=state.get("domain") or "",
            problem=state.get("problem") or "",
            error_message=errorMessage,
            lore=state["lore"]
        )
        print("\n")
        logger.debug("Refine — — risposta ricevuta:\n%s\n", refined)

        domain = extract_section(refined, "DOMAIN") or ""
        problem = extract_section(refined, "PROBLEM") or ""

        domain = strip_pddl_artifacts(domain)
        problem = strip_pddl_artifacts(problem)

        if domain == "" or problem == "":
            domain = state.get("domain_backup") or ""
            problem = state.get("problem_backup") or ""

        logger.debug("Refine — nuovo dominio e problema generati.")
        print("\n")
        print("Domain:\n", domain)
        print("\n")
        print("Problem:\n", problem)
        print("\n\n")

        attempt = state.get("attempt", 0) + 1
        return {
            "refined_domain": domain,
            "refined_problem": problem,
            "domain": domain,
            "problem": problem,
            "error_message": None,
            "attempt": attempt+1
        }
    except Exception as err:
        msg = f"Errore nel raffinamento: {err}"
        logger.error("Refine — %s", msg, exc_info=True)
        return {
            "refined_domain": None,
            "refined_problem": None,
            "error_message": msg
        }
    
def node_generate_plan(state: PDDLState) -> dict:
    """Genera il piano se la sintassi PDDL è corretta."""

    dom = state.get("domain")
    prob = state.get("problem")

    # 1) Filtro esplicito
    if dom is None or prob is None:
        msg = "Impossibile generare piano: dominio o problema mancante"
        logger.error("GeneratePlan — %s", msg)
        return {"plan": None, "plan_log": "", "error_message": msg}

    logger.info("GeneratePlan — invoco Fast Downward per il piano…")
    result = generate_plan_with_fd(dom, prob)

    if result["found_plan"]:
        logger.info("GeneratePlan — piano trovato con successo.")
        # salva anche su disco
        save_text_file("TEMP/plan.txt", result["plan"])
        return {"plan": result["plan"], "plan_log": result["log"], "error_message": None}
    else:
        logger.warning("GeneratePlan — nessun piano trovato:")
        logger.debug(result["log"])
        return {"plan": None, "plan_log": result["log"], 
                "error_message": "Nessun piano trovato: goal irraggiungibile o dominio mal modellato."}

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

def node_template_fallback(state: Mapping[str, Any]) -> Dict[str, Any]:
    lore   = state["lore"]
    domain = lore["domain"]
    problem= lore["problem"]

    env = Environment(trim_blocks=True, lstrip_blocks=True)
    DOMAIN_T  = env.from_string(domain_template_str)
    PROBLEM_T = env.from_string(problem_template_str)

    # Se ho già types e predicates in domain, salto la generazione dinamica
    dom_pddl = DOMAIN_T.render(domain=domain)
    prob_pddl= PROBLEM_T.render(problem=problem)

    print("\n")
    print("Domain Template:\n", dom_pddl)
    print("\n")
    print("Problem Template:\n", prob_pddl)
    print("\n")

    return {"domain": dom_pddl, "problem": prob_pddl, "error_message": None}

def node_human_review_initial(state: PDDLState) -> PDDLState:
    domain, problem = state["domain"], state["problem"]
    print("=== Bozza DOMAIN ===\n", domain)
    print("=== Bozza PROBLEM ===\n", problem)
    decision = input("Sono corretti? (y=ok / n=correggi): ")
    if decision.lower() != "y":
        # L’operatore incolla qui la versione corretta…
        state["domain"] = input("Inserisci DOMAIN corretto:\n")
        state["problem"] = input("Inserisci PROBLEM corretto:\n")
    return state

def end_node(state: PDDLState) -> PDDLState:
    """Nodo terminale: ritorna lo stato finale."""
    logger.info("End — fine del workflow")
    os.makedirs("TEMP", exist_ok=True)
    save_text_file("TEMP/final_domain.pddl", state.get("domain") or "")
    save_text_file("TEMP/final_problem.pddl", state.get("problem") or "")

    logger.info("Refine — raffinamento completato e file salvati")
    return state


# Aggiungiamo un contatore allo stato per il numero di tentativi
#PDDLState.__annotations__["attempt"] = int
# ---------------------
# Costruzione del grafo LangGraph
# ---------------------
# workflow = StateGraph(PDDLState)
# workflow.add_node("BuildPrompt", node_build_prompt)
# workflow.add_node("GeneratePDDL", node_generate_pddl)
# workflow.add_node("Validate", node_validate)
# workflow.add_node("Refine", node_refine)
# workflow.add_node("GeneratePlan", node_generate_plan)
# workflow.add_node("HumanReview", node_human_review_initial)
# workflow.add_node("TemplateFallback", node_template_fallback)
# workflow.add_node("End", end_node)

# workflow.set_entry_point("BuildPrompt")
# workflow.add_edge("BuildPrompt", "GeneratePDDL")
# workflow.add_edge("GeneratePDDL", "Validate")

# def validate_decision(state: PDDLState) -> str:
#     if state.get("error_message"):
#         attempt = state.get("attempt", 0)
#         if attempt + 1 > MAX_ATTEMPTS:
#             logger.error(f"🛑 Raggiunto numero massimo di tentativi ({MAX_ATTEMPTS}).")
#             domain = state.get("domain")
#             problem = state.get("problem")
#             print("\n")
#             print("Domain finale:\n", domain)
#             print("\n")
#             print("Problem finale:\n", problem)
#             print("\n")
#             return "TemplateFallback" #return "HumanReview"
#         else:
#             logger.info(f"🔁 Tentativo {attempt + 1} — avvio raffinamento.\n")
#             state["attempt"] = attempt + 1
#             return "Refine"
#     return "GeneratePlan" #"End"

# workflow.add_conditional_edges("Validate", validate_decision)
# workflow.add_edge("Refine", "Validate")
# workflow.add_edge("TemplateFallback", "Validate")
# workflow.add_edge("HumanReview", "GeneratePlan")
# workflow.add_edge("GeneratePlan", "End")

# graph = workflow.compile()

# -----------------------------------------------
# Pipeline di prova con fallback al template
# -----------------------------------------------

# workflow = StateGraph(PDDLState)
# workflow.add_node("BuildPrompt",      node_build_prompt)
# workflow.add_node("GeneratePDDL",     node_generate_pddl)
# workflow.add_node("Validate",         node_validate)
# workflow.add_node("Refine",           node_refine)
# workflow.add_node("TemplateFallback", node_template_fallback)
# workflow.add_node("GeneratePlan",     node_generate_plan)
# workflow.add_node("End",              end_node)

# workflow.set_entry_point("BuildPrompt")

# workflow.add_edge("BuildPrompt",  "GeneratePDDL")

# # Se GeneratePDDL NON estrae domain/problem -> TemplateFallback
# workflow.add_conditional_edges(
#     "GeneratePDDL",
#     path=lambda state: "TemplateFallback" if state.get("domain") is None else "Validate"
# )

# # Dopo fallback template, validiamo comunque e poi piano
# workflow.add_edge("TemplateFallback", "Validate")

# # Se Validate segnala errore -> TemplateFallback, altrimenti GeneratePlan
# workflow.add_conditional_edges(
#     "Validate",
#     path=lambda state: "TemplateFallback" if state.get("error_message") else "GeneratePlan"
# )

# workflow.add_edge("GeneratePlan", "End")

# graph = workflow.compile()

# ---------------------
# True pipeline 
# ---------------------
# ---------------------
# Costruzione del grafo LangGraph
# ---------------------
MAX_REFINE = 0

workflow = StateGraph(PDDLState)
workflow.add_node("BuildPrompt",      node_build_prompt)
workflow.add_node("GeneratePDDL",     node_generate_pddl)
workflow.add_node("Validate",         node_validate)
workflow.add_node("Refine",           node_refine)
workflow.add_node("TemplateFallback", node_template_fallback)
workflow.add_node("GeneratePlan",     node_generate_plan)
workflow.add_node("End",              end_node)

workflow.set_entry_point("BuildPrompt")
workflow.add_edge("BuildPrompt",  "GeneratePDDL")

# Se GeneratePDDL non estrae domain/problem → TemplateFallback
# workflow.add_conditional_edges(
#     "GeneratePDDL",
#     path=lambda s: "TemplateFallback" if (s.get("domain") == "" or s.get("problem") == "") else "Validate"
# )

workflow.add_conditional_edges(
    "GeneratePDDL",
    path=lambda s: "TemplateFallback" if (not s.get("domain") or not s.get("problem")) else "Validate"
)

# Se Refine non estrae domain/problem → TemplateFallback
workflow.add_conditional_edges(
    "Refine",
    path=lambda s: "TemplateFallback" if (s.get("domain") == "" or s.get("problem") == "") else "Validate"
)

# Logica di Validate:
def validate_decision(state: PDDLState) -> str:
    if not state.get("error_message"):
        return "GeneratePlan"
    attempt = state.get("attempt", 0)
    if attempt < MAX_REFINE:
        state["attempt"] = attempt + 1
        return "Refine"
    logger.info("🛑 Raggiunto numero massimo di tentativi (%d); switching to fallback template", MAX_REFINE)
    return "TemplateFallback"

workflow.add_conditional_edges("Validate", validate_decision)

# dopo un refine torno sempre a validate
workflow.add_edge("Refine", "Validate")

# una volta fatto il fallback, genero comunque il piano
workflow.add_edge("TemplateFallback", "Validate")

# dal piano → end
workflow.add_edge("GeneratePlan", "End")

graph = workflow.compile()




# ---------------------
# Test locale
# ---------------------
if __name__ == "__main__":
    LORE_PATH = "lore/example_lore.json"
    with open(LORE_PATH, encoding="utf-8") as f:
        lore_data = json.load(f)

    result = graph.invoke({
    "lore": lore_data,
    "attempt": 0
    })

    print("\n✅ DOMINIO:\n", result["domain"][:600])
    print("\n✅ PROBLEMA:\n", result["problem"][:600])
    print("\n📋 VALIDAZIONE:\n", json.dumps(result["validation"], indent=2, ensure_ascii=False))
    if result.get("refined_domain"):
        print("\n🔁 È stato eseguito un raffinamento con successo.")
        print("\n🔁 DOMINIO RAFFINATO:\n", result["refined_domain"][:600])