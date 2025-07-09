"""
Modulo per generare i file PDDL da un lore JSON, utilizzando esempi simili e un LLM locale.
"""

import os
import json
import logging
from typing import Optional

from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from game.utils import ask_ollama, extract_between, save_text_file
from db.db import retrieve_similar_examples_from_db
from game.utils import fetch_pddl_refs, fetch_pddl_snippet

from typing import Optional, List, Tuple
import json

logger = logging.getLogger(__name__)


def load_lore(lore_path: str) -> dict:
    """Carica il file di lore JSON dal percorso fornito."""
    with open(lore_path, encoding="utf-8") as f:
        return json.load(f)


def load_pddl_examples(max_examples: int = 0) -> list[tuple[str, str]]:
    """Carica esempi PDDL da sottocartelle di 'pddl_examples'."""
    examples_dir = os.path.join(os.path.dirname(__file__), "..", "pddl_examples")
    results = []

    for i, folder in enumerate(os.listdir(examples_dir)):
        if i >= max_examples:
            break
        folder_path = os.path.join(examples_dir, folder)
        if not os.path.isdir(folder_path):
            continue
        try:
            with open(os.path.join(folder_path, "domain.pddl"), encoding="utf-8") as f_dom, \
                 open(os.path.join(folder_path, "problem.pddl"), encoding="utf-8") as f_prob:
                content = f_dom.read().strip() + "\n\n" + f_prob.read().strip()
                results.append((folder, content))
        except (FileNotFoundError, OSError) as e:
            logger.warning("Errore nel caricamento dell'esempio '%s': %s", folder, e)
            continue

    return results


def retrieve_best_example(lore_text: str) -> list[tuple[str, str]]:
    """Recupera l'esempio PDDL più simile al testo del lore."""
    examples = load_pddl_examples(max_examples=0)
    if not examples:
        return []
    texts = [ex[1] for ex in examples]
    names = [ex[0] for ex in examples]
    try:
        vec = TfidfVectorizer().fit_transform(texts + [lore_text])
        vec_dense = csr_matrix(vec).toarray()
        sims = cosine_similarity(vec_dense[-1:], vec_dense[:-1]).flatten()
        best_index = sims.argmax()
        return [(names[best_index], texts[best_index])]
    except (ValueError, IndexError) as e:
        logger.warning("Errore durante la similarità: %s", e)
        return []

def build_prompt_from_lore(lore: dict, examples: Optional[List[str]] = None) -> Tuple[str, List[str]]:
    """
    Costruisce il prompt per il generatore PDDL a partire dalla lore, includendo
    opzionalmente la lista di azioni definite dall’autore.
    Restituisce una tupla (prompt, example_ids).
    """
    # Estraggo parti fisse della lore
    description     = lore.get("description", "")
    initial_state   = "\n".join(lore.get("init", []))
    goal_conditions = "\n".join(lore.get("goal", []))
    branching_cfg   = lore.get("branching")
    depth_cfg       = lore.get("depth")
    actions         = lore.get("actions", [])

    # Costruisco la sezione opzionale branching/depth
    branching_section = ""
    if branching_cfg:
        branching_section = (
            "🔀 Branching constraints:\n"
            f"- At each state, between {branching_cfg['min']} and {branching_cfg['max']} actions must be available.\n\n"
        )
    depth_section = ""
    if depth_cfg:
        depth_section = (
            "⏱️ Depth constraints:\n"
            f"- The example plan must have between {depth_cfg['min']} and {depth_cfg['max']} steps.\n\n"
        )

    # Se l’autore ha specificato le azioni nella lore, le formatto
    actions_text = ""
    if actions:
        actions_text = "— Include exactly these actions from the lore:\n"
        for act in actions:
            params = " ".join(act["parameters"])
            pres   = " ".join(act["precondition"])
            effs   = " ".join(act["effect"])
            actions_text += (
                f"(:action {act['name']}\n"
                f"  :parameters ({params})\n"
                f"  :precondition (and {pres})\n"
                f"  :effect (and {effs}))\n\n"
            )

    # Costruisco il prompt
    prompt = (
        "You are a professional PDDL generator for classical planners like Fast Downward.\n\n"
        "Your task is to generate exactly two valid PDDL files: `domain.pddl` and `problem.pddl`.\n"
        "⚠️ Use ONLY **standard PDDL syntax** — do NOT include any pseudocode or LISP extensions (e. g. '```lisp').\n\n"

        "1) TYPES & INSTANCES\n"
        "- From `lore.objects`, extract each `type` and declare it in `:types`.\n"
        "- Use object **names** only in the PROBLEM `:objects` section, never as types.\n\n"

        "2) PREDICATES\n"
        "- Infer each predicate signature from its appearances in `:init` and `:goal`.\n"
        "- Do NOT invent predicates not present in the lore facts.\n\n"

        "3) DOMAIN STRUCTURE\n"
        "- (define (domain <domain_name>))\n"
        "- (:requirements :strips :typing)\n"
        "- (:types <type1> <type2> …)\n"
        "- (:predicates (<pred1> ?x - <typeX> ?y - <typeY>) …)\n"
        "- At least one (:action <action_name> …) with :parameters, :precondition, :effect.\n\n"

        "4) SEMANTIC CONSISTENCY\n"
        "- Every predicate's declared arity and argument types must exactly match all its usages.\n"
        "- Use hyphen-separated lowercase identifiers for types, predicates, and actions.\n\n"

        f"{branching_section}"
        f"{depth_section}"
        f"{actions_text}"

        "5) PROBLEM STRUCTURE\n"
        "- (define (problem <problem_name>))\n"
        "- (:domain <domain_name>)\n"
        "- (:objects obj1 - <type1> … objN - <typeN>)\n"
        "- (:init (<pred> …) …)  # flat list of ground facts\n"
        "- (:goal (and <pred> …))\n"
        "- Every object in init/goal must be declared exactly once.\n"
        "- Every object must be declared with its type (e.g. hero - agent).\n\n"

        "6) SOLVABILITY & EXAMPLE PLAN\n"
        "- Ensure at least one valid plan exists from init to goal.\n"
        "- After the PDDL blocks, append ONLY an example plan as comments:\n"
        "  ;; Example plan:\n"
        "  ;; 1. (action1 …)\n"
        "  ;; 2. (action2 …)\n\n"

        "7) OUTPUT FORMAT\n"
        "🔁 **Return only** the two PDDL files, they must be delimited exactly as follows, with no extra text:\n"
        "=== DOMAIN START ===\n"
        "<domain.pddl>\n"
        "=== DOMAIN END ===\n\n"
        "=== PROBLEM START ===\n"
        "<problem.pddl>\n"
        "=== PROBLEM END ===\n\n"
        ";; Example plan:\n"
        ";; 1. ...\n"
        ";; 2. ...\n\n"
        
        "8) SELF-REVIEW\n"
        "- After generating both PDDL files, perform an internal consistency check:\n"
        "\t • Verify every predicate used in :init, :goal, and :action preconditions/effects is declared exactly once under :predicates.\n"
        "\t • Verify every object mentioned anywhere is declared exactly once under :objects (with the correct type).\n"
        "\t • Verify no LISP code fences or comments remain.\n"
        "\t • Ensure no ground fact from :init appears in :goal, and vice versa.\n"
        "\t • Ensure each action's parameters cover all variables used in its preconditions/effects.\n"
        "\t • Ensure that output format is right.\n"
        "- If any inconsistency is found, fix it **inline**, then re-review.\n\n"

        "— Generic example schemas (for reference only) —\n\n"

        "# Example 1\n"

        "# Generic DOMAIN schema\n"
        "(define (domain <domain_name>)\n"
        "  (:requirements :strips :typing)\n"
        "  (:types <type1> <type2>)\n"
        "  (:predicates\n"
        "    (<pred1> ?x - <type1> ?y - <type2>))\n"
        "  (:action <action1>\n"
        "    :parameters (?a - <type1> ?b - <type2>)\n"
        "    :precondition (and (<pred1> ?a ?b))\n"
        "    :effect (and (not (<pred1> ?a ?b))))\n"
        ")\n\n"

        "# Generic PROBLEM schema\n"
        "(define (problem <problem_name>)\n"
        "  (:domain <domain_name>)\n"
        "  (:objects\n"
        "    obj1 - <type1>\n"
        "    obj2 - <type2>)\n"
        "  (:init\n"
        "    (<pred1> obj1 obj2))\n"
        "  (:goal (and (<pred1> obj1 obj2)))\n"
        ")\n\n"

        "Example 2\n"

        "# Generic DOMAIN schema\n"
        "(define (domain <domain_name>)\n"
        "  (:requirements :strips :typing)\n"
        "  (:types <T1> <T2> <T3>)\n"
        "  (:predicates\n"
        "    (p1 ?x - <T1>)\n"
        "    (p2 ?x - <T1> ?y - <T2>)\n"
        "    (p3 ?z - <T3>))\n"
        "  (:action <act1>\n"
        "    :parameters (?x - <T1> ?y - <T2>)\n"
        "    :precondition (and (p2 ?x ?y))\n"
        "    :effect (and (p1 ?x) (not (p2 ?x ?y))))\n"
        "  (:action <act2>\n"
        "    :parameters (?z - <T3>)\n"
        "    :precondition (and (p3 ?z))\n"
        "    :effect (and (not (p3 ?z))))\n"
        ")\n\n"

        "# Extended PROBLEM schema\n"
        "(define (problem <prob_name>)\n"
        "  (:domain <domain_name>)\n"
        "  (:objects\n"
        "    a1 a2 - <T1>\n"
        "    b1 - <T2>\n"
        "    c1 c2 - <T3>)\n"
        "  (:init\n"
        "    (p2 a1 b1)\n"
        "    (p3 c1)\n"
        "    (p3 c2))\n"
        "  (:goal (and (p1 a1) (not (p3 c2))))\n"
        ")\n\n"


        "— Below are the lore details you must model exactly —\n\n"
        f"QUEST DESCRIPTION:\n{description}\n\n"
        f"INITIAL STATE:\n{initial_state}\n\n"
        f"GOAL CONDITIONS:\n{goal_conditions}\n\n"
    )

    # Web references

    # web_refs = fetch_pddl_refs("PDDL domain and problem Fast Downward tutorial", top_k=3)

    # print("\n\n")
    # print("Web references:", web_refs)
    # print("\n\n")

    # web_refs = fetch_pddl_refs("PDDL Fast Downward tutorial", top_k=3)
    # prompt += "\n### Web references (with snippets):\n"
    # for ref in web_refs:
    #     title, url = ref.split(" — ", 1)
    #     snippet = fetch_pddl_snippet(url)
    #     prompt += f"- **{title}** ({url})\n  {snippet}\n"

    return prompt, examples or []



def build_prompt_from_lore2(lore: dict, examples: Optional[List[str]] = None) -> Tuple[str, List[str]]:
    description     = lore.get("description", "")
    initial_state   = "\n".join(lore.get("init", []))
    goal_conditions = "\n".join(lore.get("goal", []))
    branching_cfg   = lore.get("branching")
    depth_cfg       = lore.get("depth")
    actions         = lore.get("actions", [])

    branching_section = ""
    if branching_cfg:
        branching_section = (
            "🔀 Branching constraints:\n"
            f"- At each state, between {branching_cfg['min']} and {branching_cfg['max']} actions must be available.\n\n"
        )
    depth_section = ""
    if depth_cfg:
        depth_section = (
            "⏱️ Depth constraints:\n"
            f"- The example plan must have between {depth_cfg['min']} and {depth_cfg['max']} steps.\n\n"
        )
    
    actions_text = ""
    if actions:
        actions_text = "— Include exactly these actions from the lore:\n"
        for act in actions:
            params = " ".join(act["parameters"])
            pres   = " ".join(act["precondition"])
            effs   = " ".join(act["effect"])
            actions_text += (
                f"(:action {act['name']}\n"
                f"  :parameters ({params})\n"
                f"  :precondition (and {pres})\n"
                f"  :effect (and {effs}))\n\n"
            )

    prompt = (
        "You are a professional PDDL generator for classical planners like Fast Downward.\n"
        "\n"
        "Your task is to generate exactly two valid PDDL files: `domain.pddl` and `problem.pddl`.\n"
        "⚠️ Use ONLY **standard PDDL syntax** — do NOT include any pseudocode or LISP extensions (e.g. '```lisp').\n"
        "\n"
        "⚠️ **All output must be wrapped exactly** as follows (no extra text, no omissions):\n"
        "\n"
        "=== DOMAIN START ===\n"
        "<complete, valid PDDL domain>\n"
        "=== DOMAIN END ===\n"
        "\n"
        "=== PROBLEM START ===\n"
        "<complete, valid PDDL problem>\n"
        "=== PROBLEM END ===\n"
        "\n"
        ";; Example plan:\n"
        ";; 1. (action1 …)\n"
        ";; 2. (action2 …)\n"
        "\n"
        "Do not add, remove, or rename these markers under any circumstances.\n"
        "\n"
        "## 1) METADATA\n"
        "\n"
        "QUEST DESCRIPTION:\n"
        f"{description}\n"
        "\n"
        "INITIAL STATE (flat facts):\n"
        f"{initial_state}\n"
        "\n"
        "GOAL CONDITIONS:\n"
        f"{goal_conditions}\n"
        "\n"
        f"{actions_text}\n"
        f"{branching_section}\n"
        f"{depth_section}\n"
        "\n"
        "2) DOMAIN TEMPLATE\n"
        "\n"
        "=== DOMAIN START ===\n"
        "(define (domain <domain_name>)\n"
        "  (:requirements :strips :typing)\n"
        "  (:types\n"
        "    <type1> <type2> …\n"
        "  )\n"
        "  (:predicates\n"
        "    (<pred1> ?x - <typeX> ?y - <typeY>)\n"
        "    …\n"
        "  )\n"
        "  # For each action, infer the full :parameters list by scanning its :precondition and :effect clauses, and include every variable you find (even if not listed in lore.actions).\n"
        "  # Then verify no variable is used without declaration.\n"
        "  <for each action in lore.actions>\n"
        "  (:action <action_name>\n"
        "    :parameters (?p1 - <typeP1> ?p2 - <typeP2> …)\n"
        "    :precondition (and <preds…>)\n"
        "    :effect       (and <effects…>)\n"
        "  )\n"
        ")\n"
        "=== DOMAIN END ===\n"
        "\n"
        "3) PROBLEM TEMPLATE\n"
        "\n"
        "=== PROBLEM START ===\n"
        "(define (problem <problem_name>)\n"
        "  (:domain <domain_name>)\n"
        "  (:objects\n"
        "    obj1 - <type1>\n"
        "    obj2 obj3 - <type2>\n"
        "    …\n"
        "  )\n"
        "  (:init\n"
        "    <each init fact exactly once>\n"
        "  )\n"
        "  (:goal\n"
        "    (and\n"
        "      <each goal fact>\n"
        "    )\n"
        "  )\n"
        ")\n"
        "=== PROBLEM END ===\n"
        "\n"
        "## 4) SELF-REVIEW\n"
        "\n"
        "1. Marker check: ensure both start/end markers are present and correctly spelled.\n"
        "2. Type check: every object has a `- <type>`; no types in `:objects` without matching `:types`.\n"
        "3. Predicate check: every predicate used anywhere is declared exactly once under `:predicates`.\n"
        "4. Arity & naming: argument counts and types match across definitions and uses; identifiers lowercase, hyphen-separated.\n"
        "5. No fences: remove any Markdown or LISP code fences.\n"
        "\n"
        "## 5) OUTPUT\n"
        "\n"
        "Return only the two PDDL files delimited by the markers above and a two-line example plan in comments.\n"
        "No additional commentary or explanation.\n"
    )

    return prompt, examples or []


def build_prompt_from_lore3(lore: dict, examples: Optional[List[str]] = None) -> Tuple[str, List[str]]:
    description     = lore.get("description", "")
    initial_state   = "\n".join(lore.get("init", []))
    goal_conditions = "\n".join(lore.get("goal", []))
    branching_cfg   = lore.get("branching")
    depth_cfg       = lore.get("depth")
    actions         = lore.get("actions", [])

    branching_section = ""
    if branching_cfg:
        branching_section = (
            "🔀 Branching constraints:\n"
            f"- At each state, between {branching_cfg['min']} and {branching_cfg['max']} actions must be available.\n\n"
        )
    depth_section = ""
    if depth_cfg:
        depth_section = (
            "⏱️ Depth constraints:\n"
            f"- The example plan must have between {depth_cfg['min']} and {depth_cfg['max']} steps.\n\n"
        )
    
    actions_text = ""
    if actions:
        actions_text = "— Include exactly these actions from the lore:\n"
        for act in actions:
            params = " ".join(act["parameters"])
            pres   = " ".join(act["precondition"])
            effs   = " ".join(act["effect"])
            actions_text += (
                f"(:action {act['name']}\n"
                f"  :parameters ({params})\n"
                f"  :precondition (and {pres})\n"
                f"  :effect (and {effs}))\n\n"
            )
    
    if examples:
        few_shot_section = "\n\n".join(examples) + "\n\n"
    else:
        # qui inserisci la tua versione statica
        few_shot_section = ""

    lore_json = json.dumps(lore, indent=2, ensure_ascii=False)
    prompt = (
        "You are a PDDL expert.\n"
        "Please use the following examples for illustrative purposes only.\n\n"
        f"{few_shot_section}"
        "## 2) DOMAIN TEMPLATE (STRICT)\n\n"
        "=== DOMAIN START ===\n"
        "(define (domain <domain_name>)\n"
        "  (:requirements :strips :typing)\n"
        "  (:types <type1> <type2> …)\n"
        "  (:predicates\n"
        "    (<pred1> ?x - <typeX> ?y - <typeY>)\n"
        "    …\n"
        "  )\n"
        "  ; No hard-coded object names here — use only variables (starting with `?`). DO NOT use constants here.\n"
        "  (:action <action_name>\n"
        "    :parameters (?p1 - <typeP1> …)\n"
        "    :precondition (and …)\n"
        "    :effect (and …)\n"
        "  )\n"
        "  …\n"
        ")\n"
        "=== DOMAIN END ===\n\n"

        "## 3) PROBLEM TEMPLATE\n\n"
        "=== PROBLEM START ===\n"
        "(define (problem <problem_name>)\n"
        "  (:domain <domain_name>)\n"
        "   ; Declare all objects (the hard-coded one also) here, including constants\n"
        "  (:objects\n"
        "    obj1 obj2 - object\n"
        "    r1 r2     - vehicle\n"
        "    loc1 loc2 - location\n"
        "  )\n"
        "  (:init\n"
        "    <all init facts>\n"
        "  )\n"
        "  (:goal (and <all goal facts>))\n"
        ")\n"
        "=== PROBLEM END ===\n\n"

        "Follow these steps exactly.\n\n"

        # STEP 1
        "--- STEP 1: LORE → JSON  \n"
        "Read the following lore (as valid JSON) and output **only** valid JSON with exactly these keys:\n"
        "domain_name, problem_name, types, predicates, objects, constants, init, goal, actions.\n\n"
        " The field 'constants' lists **all** the concrete names.  In STEP 2 you must **not** invent other constants."
        "Here is the lore as JSON:\n"
        "```json\n"
        f"{lore_json}\n"
        "```\n\n"

        # STEP 2
        "--- STEP 2: JSON → PDDL  \n"
        "Take the JSON you produced and generate exactly two PDDL files—no code fences, no Markdown, **no** :constants—\n"
        "only standard STRIPS+typing. Enforce `(:requirements :strips :typing)` and no other requirements.\n\n"
        "—in the PROBLEM file, include **both** your 'objects' **and** your 'constants' under (:objects …)."
        "—in the DOMAIN file, **never** hardcode any name from 'constants'; use only parameters (starting with ?)."
        "🔄 **Parameterize all constants in actions**  \n"
        "Whenever you see a predicate in an action's precondition or effect that refers to a concrete object, you **must**:\n"
        "1. Introduce a fresh variable in the action's `:parameters` list (e.g. `?s - object`).\n"
        "2. Replace the constant with that variable (e.g. `(on_ground ?s ?l)`).\n"
        "3. **Never** leave hard-coded names in the DOMAIN—everything there must be a `?`-variable.\n"
        "Concrete object names belong **only** in the PROBLEM's `:objects` section.\n\n"

        # Emphasis su variabili vs oggetti concreti
        "🔑 **IMPORTANT: Variables vs. Objects**\n"
        "1. In the **DOMAIN**, **only** use **variables** (they must start with `?` and be declared in `:parameters`).\n"
        "2. **Do not** hard-code any concrete object name in the DOMAIN's predicates, preconditions or effects.\n"
        "3. All concrete objects (like `sword_of_fire`, `ice_dragon`, etc.) belong **only** in the PROBLEM's `:objects` section.\n\n"

        "Wrap them exactly like this:\n\n"
        "=== DOMAIN START ===\n"
        "(define (domain <domain_name>)\n"
        "  (:requirements :strips :typing)\n"
        "  (:types <type1> <type2> …)\n"
        "  (:predicates\n"
        "    (<pred1> ?x - <typeX> ?y - <typeY>)\n"
        "    …\n"
        "  )\n"
        "  ; No concrete names here\n"
        "  (:action <action1>\n"
        "    :parameters (?p1 - <typeP1> …)\n"
        "    :precondition (and …)\n"
        "    :effect (and …)\n"
        "  )\n"
        ")\n"
        "=== DOMAIN END ===\n\n"

        "=== PROBLEM START ===\n"
        "(define (problem <problem_name>)\n"
        "  (:domain <domain_name>)\n"
        "  (:objects\n"
        "    <obj1> - <type1>\n"
        "    <obj2> <obj3> - <type2>\n"
        "    …\n"
        "  )\n"
        "  (:init\n"
        "    <each init fact>\n"
        "  )\n"
        "  (:goal (and\n"
        "    <each goal fact>\n"
        "  ))\n"
        ")\n"
        "=== PROBLEM END ===\n\n"

        # STEP 2.5
        "--- STEP 2.5: FAST DOWNWARD PREDICTION  \n"
        "Predict which Fast Downward exit code this PDDL would return (0, 1-3, 10-12, 20-21, 22-24, 30, 31, etc.)\n"
        "and give a one-sentence rationale. Do not repair yet.\n\n"

        # STEP 3
        "--- STEP 3: SELF-CHECK  \n"
        "Before returning, list any issues you found (empty list if none), verifying exactly:\n"
        "1. Presence of correct markers.\n"
        "2. All types used are declared.\n"
        "3. All predicates used are declared.\n"
        "4. Variables in parameters match those in preconditions/effects.\n"
        "5. Objects in init/goal match those in the objects list.\n"
        "6. DOMAIN uses only variables; PROBLEM uses only concrete names.\n\n"
        "If there are issues, correct them; otherwise return:\n"
        "- the JSON from step 1\n"
        "- the PDDL files from step 2\n"
        "- the predicted exit code from step 2.5\n"
        "- “No issues.”\n"
    )

    return prompt, examples or []


def build_prompt_from_lore4(lore: dict, examples: Optional[List[str]] = None) -> Tuple[str, List[str]]:
    description     = lore.get("description", "")
    initial_state   = "\n".join(lore.get("init", []))
    goal_conditions = "\n".join(lore.get("goal", []))
    branching_cfg   = lore.get("branching")
    depth_cfg       = lore.get("depth")
    actions         = lore.get("actions", [])

    branching_section = ""
    if branching_cfg:
        branching_section = (
            "🔀 Branching constraints:\n"
            f"- At each state, between {branching_cfg['min']} and {branching_cfg['max']} actions must be available.\n\n"
        )
    depth_section = ""
    if depth_cfg:
        depth_section = (
            "⏱️ Depth constraints:\n"
            f"- The example plan must have between {depth_cfg['min']} and {depth_cfg['max']} steps.\n\n"
        )
    
    actions_text = ""
    if actions:
        actions_text = "— Include exactly these actions from the lore:\n"
        for act in actions:
            params = " ".join(act["parameters"])
            pres   = " ".join(act["precondition"])
            effs   = " ".join(act["effect"])
            actions_text += (
                f"(:action {act['name']}\n"
                f"  :parameters ({params})\n"
                f"  :precondition (and {pres})\n"
                f"  :effect (and {effs}))\n\n"
            )
    
    if examples:
        few_shot_section = "\n\n".join(examples) + "\n\n"
    else:
        # qui inserisci la tua versione statica
        few_shot_section = ""

    lore_json = json.dumps(lore, indent=2, ensure_ascii=False)
    prompt = (
        "You are a PDDL expert.\n"
        "Take the following JSON input (lore_json) and generate **only** two PDDL blocks:\n\n"

        "=== DOMAIN START ===\n"
        "(define (domain <domain_name>)\n"
        "  (:requirements :strips :typing)\n"
        "  (:types <type1> <type2> …)\n"
        "  (:predicates\n"
        "    (<pred1> ?arg1 - <type1> ?arg2 - <type2>)\n"
        "    …\n"
        "  )\n"
        "  (:action <action_name>\n"
        "    :parameters (?p1 - <typeP1> …)\n"
        "    :precondition (and …)\n"
        "    :effect (and …)\n"
        "  )\n"
        ")\n"
        "=== DOMAIN END ===\n\n"

        "=== PROBLEM START ===\n"
        "(define (problem <problem_name>)\n"
        "  (:domain <domain_name>)\n"
        "  (:objects\n"
        "    obj1 obj2 - <typeX>\n"
        "    …\n"
        "  )\n"
        "  (:init\n"
        "    <all init facts>\n"
        "  )\n"
        "  (:goal (and\n"
        "    <all goal facts>\n"
        "  ))\n"
        ")\n"
        "=== PROBLEM END ===\n\n"

        "Rules:\n"
        "- In the DOMAIN: use only variables (prefixed with `?`) and parameterize any constants.\n"
        "- In the PROBLEM: list all concrete objects and constants under `(:objects ...)`.\n"
        "- Enforce only `:requirements :strips :typing`, no others.\n"
        "- Do **not** generate JSON or explanations: output exactly the two PDDL blocks with their markers.\n\n"

        "Here is the input JSON:\n"
        "```json\n"
        f"{lore_json}\n"
        "```\n"
    )


    return prompt, examples or []


def generate_pddl_from_lore(lore_path: str) -> tuple[Optional[str], Optional[str], list[str]]:
    """Genera i file PDDL a partire da un file JSON di lore."""
    lore = load_lore(lore_path)
    return generate_pddl_from_dict(lore, lore_path)


def generate_pddl_from_dict(
    lore: dict,
    lore_path: Optional[str] = None
) -> tuple[Optional[str], Optional[str], list[str]]:
    """Genera i file PDDL a partire da un dizionario di lore."""
    prompt, used_examples = build_prompt_from_lore(lore)
    raw = ask_ollama(prompt)

    if lore_path:
        session_dir = os.path.join("uploads", os.path.basename(lore_path).split(".")[0])
        os.makedirs(session_dir, exist_ok=True)
        save_text_file(os.path.join(session_dir, "raw_llm_response.txt"), raw)

    domain = extract_between(raw, "=== DOMAIN START ===", "=== DOMAIN END ===")
    problem = extract_between(raw, "=== PROBLEM START ===", "=== PROBLEM END ===")

    if not domain or not problem or not domain.strip().lower().startswith("(define"):
        logger.warning("⚠️ Generazione fallita: PDDL non valido.")
        return None, None, used_examples

    return domain, problem, used_examples