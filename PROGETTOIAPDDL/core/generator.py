"""
Modulo per generare i file PDDL da un lore, gestendo sia dict strutturati che plain text.
"""

import os
import json
from pathlib import Path
import logging
from typing import Optional, Tuple, List, Dict, Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import csr_matrix

from core.utils import ask_ollama, extract_between, save_text_file
from core.validator import validate_pddl

from langchain_core.tools import tool

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@tool
def generate_pddl_tool(data: dict) -> dict:
    """
    Tool compatibile LangChain: genera PDDL da un lore dict o da path.
    """
    lore = data.get("lore") or data.get("description")
    lore_path = data.get("lore_path")

    if isinstance(lore, dict):
        domain, problem, examples = generate_pddl_from_dict(lore, lore_path)
    elif isinstance(lore, str):
        try:
            lore_obj = json.loads(lore)
            domain, problem, examples = generate_pddl_from_dict(lore_obj, lore_path)
        except Exception as e:
            return {"error": f"Invalid lore JSON: {str(e)}"}
    else:
        return {"error": "No valid lore provided"}

    return {
        "domain": domain,
        "problem": problem,
        "examples_used": examples
    }


def load_lore(lore_path: str) -> dict:
    with open(lore_path, encoding="utf-8") as f:
        return json.load(f)


def load_pddl_examples(max_examples: int = 5) -> List[Tuple[str, str]]:
    examples_dir = os.path.join(os.path.dirname(__file__), "..", "pddl_examples")
    results: List[Tuple[str, str]] = []
    for i, folder in enumerate(os.listdir(examples_dir)):
        if max_examples > 0 and i >= max_examples:
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
            logger.warning("⚠️ Errore caricamento esempio '%s': %s", folder, e)
            continue
    return results

def retrieve_best_example(lore_text: str, k: int = 1) -> List[Tuple[str, str]]:
    examples = load_pddl_examples()
    if not examples:
        return []

    texts = [ex[1] for ex in examples]
    names = [ex[0] for ex in examples]

    try:
        vec = TfidfVectorizer().fit_transform(texts + [lore_text])
        #vec_dense = vec.tocsr().toarray()
        vec_dense = csr_matrix(vec).toarray()
        sims = cosine_similarity(vec_dense[-1].reshape(1, -1), vec_dense[:-1]).flatten()
        top_indices = sims.argsort()[::-1][:k]
        return [(names[i], texts[i]) for i in top_indices]
    except Exception as e:
        logger.warning("Errore calcolo similarità RAG: %s", e)
        return []

def generate_pddl_from_dict(
    lore: dict,
    lore_path: Optional[str] = None
) -> Tuple[Optional[str], Optional[str], List[str]]:
    # Step 1: Recupera esempi più simili
    description_text = lore.get("description", "")
    example_pairs = retrieve_best_example(description_text, k=1)  # usa anche k=2 se vuoi più esempi
    example_texts = [content for _, content in example_pairs]

    # Step 2: Costruisci il prompt con gli esempi
    prompt, used_example_names = build_prompt_from_lore(lore, example_texts)

    # Step 3: Chiedi al LLM
    raw = ask_ollama(prompt)

    # Step 4: Salva risposta raw per debug
    session_dir = os.path.join(
        "uploads", "tmp" if not lore_path else os.path.basename(lore_path).split(".")[0]
    )
    os.makedirs(session_dir, exist_ok=True)
    save_text_file(os.path.join(session_dir, "raw_llm_response.txt"), raw)

    # Step 5: Estrai i blocchi
    domain = extract_between(raw, "=== DOMAIN START ===", "=== DOMAIN END ===")
    problem = extract_between(raw, "=== PROBLEM START ===", "=== PROBLEM END ===")

    # Step 6: Validazione
    if not domain or not problem or not domain.strip().lower().startswith("(define"):
        logger.warning("Generazione fallita: PDDL non valido.")
        return None, None, used_example_names

    validation = validate_pddl(domain, problem, lore)
    if not validation["valid_syntax"]:
        logger.warning("Validazione fallita: %s", json.dumps(validation, indent=2))
        save_text_file(
            os.path.join(session_dir, "validation_failed.json"),
            json.dumps(validation, indent=2)
        )
        return None, None, used_example_names

    return domain, problem, used_example_names



def generate_pddl_from_lore(lore_path: str) -> Tuple[Optional[str], Optional[str], List[str]]:
    lore = load_lore(lore_path)
    return generate_pddl_from_dict(lore, lore_path)

def build_prompt_from_lore1(lore: dict, examples: Optional[List[str]] = None) -> Tuple[str, List[str]]:
    examples = examples or []
    examples_text = ""
    for i, content in enumerate(examples):
        if "(define" in content and "(:action" in content:
            examples_text += f"\n// ---- Example {i+1} ----\n{content.strip()}\n"

    is_plain = set(lore.keys()) <= {"description"}

    prompt_path = Path("prompts/generator/generator_prompt3.txt")
    if prompt_path.exists():
        intro = prompt_path.read_text(encoding="utf-8")
    else:
        intro = """
            You are a professional assistant for generating classical PDDL files (Planning Domain Definition Language).
            Your task is to produce two complete, syntactically valid and logically consistent PDDL files:
            - domain.pddl
            - problem.pddl

            🧠 These files will be validated automatically for:
            • Syntactic correctness (valid parentheses, required sections, correct parameter types)
            • Semantic coherence between domain/problem/init/goal
            • Consistency with the provided lore: description, objects, initial state, and goal

            🔒 STRICT CONSTRAINTS — DO NOT violate these:
            1. NEVER hardcode specific objects like 'sword_of_fire' or 'ice_dragon' in the domain file.
            → Use generic parameters like ?o - object, ?m - monster, etc.
            2. Each :action must define all required parameters explicitly and assign types correctly.
            → Example: (:parameters (?a - agent ?o - object ?l - location))
            3. Each predicate must follow the format: (predicate ?x - type ?y - type)
            → ❌ Wrong: (at ?a ?l) - (agent location)
            → ✅ Correct: (at ?a - agent ?l - location)
            4. Use ONLY objects, predicates and goals listed in the lore.
            5. Use :precondition and :effect sections correctly (no plural).
            6. Use valid STRIPS-compatible syntax: :types, :predicates, :action.
            7. Use ; comments to clarify each section.
            8. Your output MUST follow this format exactly:

            === DOMAIN START ===
            <insert domain.pddl here>
            === DOMAIN END ===
            === PROBLEM START ===
            <insert problem.pddl here>
            === PROBLEM END ===
            """
    if is_plain:
        lore_text = lore.get("description", "")
        prompt = (
            intro +
            f"\nQUEST DESCRIPTION:\n{lore_text}\n\n"
        )
    else:
        required_keys = ["init", "goal", "objects"]
        for key in required_keys:
            if key not in lore or not lore[key]:
                raise ValueError(f"❌ Lore incompleto: manca '{key}'")

        initial_state = "\n".join(lore["init"])
        goal_conditions = "\n".join(lore["goal"])
        object_list = "\n".join(lore["objects"])

        branching = lore.get("branching_factor", {"min": 1, "max": 4})
        depth = lore.get("depth_constraints", {"min": 3, "max": 10})

        prompt = (
            intro +
            "\nOBJECTS:\n" + object_list + "\n\n" +
            "INITIAL STATE:\n" + initial_state + "\n\n" +
            "GOAL CONDITIONS:\n" + goal_conditions + "\n\n" +
            f"BRANCHING FACTOR: min {branching['min']}, max {branching['max']}\n" +
            f"DEPTH CONSTRAINTS: min {depth['min']}, max {depth['max']}\n\n" +
            f"QUEST TITLE: {lore.get('quest_title', '(not provided)')}\n" +
            f"WORLD CONTEXT: {lore.get('world_context', '(not provided)')}\n" +
            f"NARRATIVE DESCRIPTION:\n{lore.get('description', '')}\n"
        )

    if examples_text:
        prompt += "\n📚 REFERENCE EXAMPLES:\n" + examples_text

    # Output format obbligatorio
    prompt += (
        "\n\nYour output MUST follow this format:\n"
        "=== DOMAIN START ===\n<insert domain.pddl here>\n=== DOMAIN END ===\n"
        "=== PROBLEM START ===\n<insert problem.pddl here>\n=== PROBLEM END ===\n"
    )

    return prompt, [f"Example {i+1}" for i in range(len(examples))]

def build_prompt_from_lore(lore: Dict[str, Any], examples: Optional[List[str]] = None) -> Tuple[str, List[str]]:
    """
    Legge da file un template di prompt e lo riempie con:
      - description, objects, init, goal (sempre come stringhe)
      - se presenti, branching, depth, actions
      - esempi few-shot (se presenti)
    Se qualche campo manca, viene sostituito con stringa vuota o lista vuota.
    """
    # 1) Carica template
    prompt_path = "prompts/generator/generator_prompt2.txt"
    tpl = Path(prompt_path)
    if not tpl.exists():
        raise FileNotFoundError(f"Prompt template not found at: {prompt_path}")
    template = tpl.read_text(encoding="utf-8")

    # 2) Estrai e normalizza i campi da lore
    description     = lore.get("description") or ""
    if not isinstance(description, str):
        description = str(description)

    objects = lore.get("objects") or []
    if not isinstance(objects, list):
        objects = []
    objects_list = "\n".join(str(o) for o in objects)

    initial = lore.get("init") or []
    if not isinstance(initial, list):
        initial = []
    initial_state = "\n".join(str(f) for f in initial)

    goal = lore.get("goal") or []
    if not isinstance(goal, list):
        goal = []
    goal_conditions = "\n".join(str(g) for g in goal)

    branching = lore.get("branching")
    if not (isinstance(branching, dict)
            and "min" in branching and "max" in branching):
        branching = None

    depth = lore.get("depth")
    if not (isinstance(depth, dict)
            and "min" in depth and "max" in depth):
        depth = None

    actions = lore.get("actions") or []
    if not isinstance(actions, list):
        actions = []

    # 3) Costruisci sezioni opzionali
    branching_section = ""
    if branching:
        branching_section = (
            "🔀 Branching constraints:\n"
            f"- At each state, there must be between {branching['min']} "
            f"and {branching['max']} available actions.\n\n"
        )

    depth_section = ""
    if depth:
        depth_section = (
            "⏱️ Depth constraints:\n"
            f"- The example plan must have between {depth['min']} "
            f"and {depth['max']} steps.\n\n"
        )

    actions_section = ""
    if actions:
        actions_section = "📜 Actions defined in lore:\n"
        for act in actions:
            name = act.get("name", "<unnamed>")
            params = act.get("parameters") or []
            if not isinstance(params, list):
                params = []
            pres = act.get("precondition") or []
            if not isinstance(pres, list):
                pres = []
            effs = act.get("effect") or []
            if not isinstance(effs, list):
                effs = []

            params_str = " ".join(f"?{p}" for p in params)
            pres_str   = " ".join(str(p) for p in pres)
            effs_str   = " ".join(str(e) for e in effs)

            actions_section += (
                f"(:action {name}\n"
                f"  :parameters ({params_str})\n"
                f"  :precondition (and {pres_str})\n"
                f"  :effect (and {effs_str}))\n\n"
            )

    # 4) Few-shot
    few_shot_block = ""
    if examples:
        few_shot_block = (
            "\n\n--- Few-Shot Examples ---\n"
            + "\n\n".join(str(x) for x in examples)
            + "\n"
        )

    # 5) Popola il template
    try:
        prompt = template.format(
            DESCRIPTION=description.strip(),
            OBJECTS=objects_list,
            INIT=initial_state,
            GOAL=goal_conditions,
            BRANCHING=branching_section,
            DEPTH=depth_section,
            ACTIONS=actions_section,
            FEW_SHOT=few_shot_block
        )
    except KeyError as e:
        missing = e.args[0]
        raise KeyError(f"Template placeholder {{{missing}}} not provided by code") from e

    return prompt, examples or []