import os
import json
import logging
from typing import TypedDict, Optional
from jinja2 import Template

from langgraph.graph import StateGraph
from game.generator import build_prompt_from_lore, build_prompt_from_lore4
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

    logger.info("✅ Lore pronta all’uso.\n")

    few_shot_examples = load_few_shot_examples("examples", max_examples=3)
    prompt, *_ = build_prompt_from_lore4(lore, few_shot_examples)

    # print("\n")
    # logger.debug("BuildPrompt — prompt generato:\n%s\n", prompt)
    # print("\n")

    state["prompt"] = prompt
    logger.debug(f"📄 Prompt generato (inizio):\n{prompt[:700]}...\n\n")
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
        logger.debug("Refine — avvio con error_message: %s\n", state.get("error_message"))
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
            "attempt": attempt
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
    


DOMAIN_TEMPLATE = Template(r"""
(define (domain {{ domain_name }})
  (:requirements :strips :typing){% if types %}
  (:types {{ types|join(" ") }}){% endif %}{% if predicates %}
  (:predicates
  {%- for p in predicates %}
    {{ p }}
  {%- endfor %}
  ){% endif %}
{%- for act in actions %}
  (:action {{ act.name }}
    :parameters ({% for param in act.parameters %}?{{param.name}} - {{param.type}}{% if not loop.last %} {% endif %}{% endfor %})
    :precondition (and{% for pre in act.precondition %} {{ pre }}{% endfor %})
    :effect       (and{% for eff in act.effect       %} {{ eff }}{% endfor %})
  )
{%- endfor %}
)
""".strip())

PROBLEM_TEMPLATE = Template(r"""
(define (problem {{ problem_name }})
  (:domain {{ domain_name }})
  (:objects
  {%- for typ, objs in objects_by_type.items() %}
    {{ objs|join(" ") }} - {{ typ }}
  {%- endfor %}
  )
  (:init
  {%- for fact in init %}
    {{ fact }}
  {%- endfor %}
  )
  (:goal (and{% for g in goal %} {{ g }}{% endfor %}))
)
""".strip())

def node_template_fallback(state: PDDLState) -> dict:
    lore = state["lore"]
    domain_name  = lore.get("domain_name", "my-domain")
    problem_name = lore.get("problem_name", "my-problem")
    constants    = lore.get("constants", [])
    objects      = lore.get("objects", [])
    init         = lore.get("init", [])
    goal         = lore.get("goal", [])
    actions      = lore.get("actions", [])

    # 1) constant → tipo
    const_type = {
        c.split(" - ")[0].strip(): c.split(" - ")[1].strip()
        for c in constants
    }

    # 1b) var_type_map: tutti i ?variabili già dichiarati in TUTTE le azioni
    var_type_map = {}
    for act in actions:
        for p in act["parameters"]:
            name, typ = [x.strip() for x in p.lstrip("?").split(" - ")]
            var_type_map[name] = typ

    # 2) processa azioni e parameterizza concreti e variabili mancanti
    processed = []
    for act in actions:
        # parametri iniziali
        params = []
        for p in act["parameters"]:
            v, t = [x.strip() for x in p.lstrip("?").split(" - ")]
            params.append({"name": v, "type": t})

        preconds = list(act["precondition"])
        effects  = list(act["effect"])
        for lst in (preconds, effects):
            for i, lit in enumerate(lst):
                toks = lit.strip("()").split()
                for tok in toks[1:]:
                    if tok.startswith("?"):
                        var = tok.lstrip("?")
                        # se var non è già dichiarata e la conosciamo da var_type_map:
                        if var not in [p["name"] for p in params] and var in var_type_map:
                            params.append({"name": var, "type": var_type_map[var]})
                            lit = lit.replace(f" {tok}", f" {tok}")
                    else:
                        # concreti come sword_of_fire
                        if tok in const_type:
                            var = tok
                            if var not in [p["name"] for p in params]:
                                params.append({"name": var, "type": const_type[var]})
                            lit = lit.replace(f" {tok}", f" ?{tok}")
                lst[i] = lit

        processed.append({
            "name":         act["name"],
            "parameters":   params,
            "precondition": preconds,
            "effect":       effects
        })

    # 3) raccogli i predicati unici
    pred_map = {}
    def collect(lits):
        for lit in lits:
            parts = lit.strip("()").split()
            pred = parts[0]
            if pred in ("and", "not", "or", "="): continue
            args = parts[1:]
            arg_list = []
            for a in args:
                var = a.lstrip("?")
                typ = None
                # cerca tipo fra i params elaborati
                for act in processed:
                    for p in act["parameters"]:
                        if p["name"] == var:
                            typ = p["type"]
                # fallback su const_type
                if typ is None and var in const_type:
                    typ = const_type[var]
                if typ is None:
                    typ = "object"
                arg_list.append((var, typ))
            pred_map[pred] = arg_list

    collect(init)
    collect(goal)
    for act in processed:
        collect(act["precondition"])
        collect(act["effect"])

    predicates = [
        f"({name} {' '.join(f'?{v} - {t}' for v,t in args)})"
        for name, args in pred_map.items()
    ]

    # 4) tipi unici
    types_set = set()
    for p in processed:
        for pr in p["parameters"]:
            types_set.add(pr["type"])
    for _, args in pred_map.items():
        for _, t in args:
            types_set.add(t)
    types = sorted(types_set)

    # 5) oggetti per PROBLEM
    objects_by_type = {}
    for entry in objects + constants:
        n, typ = [x.strip() for x in entry.split(" - ")]
        objects_by_type.setdefault(typ, []).append(n)
    for typ in objects_by_type:
        objects_by_type[typ] = sorted(set(objects_by_type[typ]))

    # 6) render
    domain = DOMAIN_TEMPLATE.render(
        domain_name=domain_name,
        types=types,
        predicates=predicates,
        actions=processed
    ).strip()
    problem = PROBLEM_TEMPLATE.render(
        problem_name=problem_name,
        domain_name=domain_name,
        objects_by_type=objects_by_type,
        init=init,
        goal=goal
    ).strip()

    print("\n")
    print("Template Domain:\n", domain)
    print("\n")
    print("Template Problem:\n", problem)
    print("\n")

    return {"domain": domain, "problem": problem, "error_message": None}


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



MAX_ATTEMPTS = 3  # Numero massimo di tentativi

# Aggiungiamo un contatore allo stato per il numero di tentativi
PDDLState.__annotations__["attempt"] = int
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
MAX_REFINE = 3

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
workflow.add_conditional_edges(
    "GeneratePDDL",
    path=lambda s: "TemplateFallback" if (s.get("domain") is "" or s.get("problem") is "") else "Validate"
)

# Se Refine non estrae domain/problem → TemplateFallback
workflow.add_conditional_edges(
    "Refine",
    path=lambda s: "TemplateFallback" if (s.get("domain") is "" or s.get("problem") is "") else "Validate"
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