"""
Modulo per generare i file PDDL da un lore, gestendo sia dict strutturati che plain text.
"""

import os
import json
import logging
from typing import Optional, Tuple, List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from core.utils import ask_ollama, extract_between, save_text_file
from core.validator import validate_pddl

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)




from langchain_core.tools import tool

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


def retrieve_best_example(lore_text: str) -> List[Tuple[str, str]]:
    examples = load_pddl_examples(max_examples=5)
    if not examples:
        return []
    texts = [ex[1] for ex in examples]
    names = [ex[0] for ex in examples]
    try:
        vec = TfidfVectorizer().fit_transform(texts + [lore_text])
        sims = cosine_similarity(vec[-1], vec[:-1]).flatten()
        best_index = sims.argmax()
        return [(names[best_index], texts[best_index])]
    except (ValueError, IndexError) as e:
        logger.warning("⚠️ Errore similarità: %s", e)
        return []


def build_prompt_from_lore(lore: dict, examples: Optional[List[str]] = None) -> Tuple[str, List[str]]:
    examples = examples or []
    examples_text = ""
    for i, content in enumerate(examples):
        if "(define" in content and "(:action" in content:
            examples_text += f"\n// ---- Example {i+1} ----\n{content.strip()}\n"

    is_plain = set(lore.keys()) <= {"description"}

    intro = (
        "You are a professional PDDL generation assistant.\n"
        "Your task is to produce two complete, valid and logically consistent PDDL files:\n"
        "- `domain.pddl`\n"
        "- `problem.pddl`\n\n"
        "💡 These files will be automatically validated for:\n"
        "• Syntactic correctness (PDDL standards)\n"
        "• Object/predicate coherence across domain/problem/init/goal\n"
        "• Full consistency with the lore provided\n\n"
        "📏 Please follow these STRICT constraints:\n"
        "1. Use ONLY objects, types and predicates from the lore.\n"
        "2. Each predicate in the goal must be declared and used.\n"
        "3. Init and goal must match exactly the lore.\n"
        "4. Use valid and modular PDDL syntax, with correct parentheses.\n"
        "5. Comment each line with a `;` explaining its purpose.\n"
        "6. Do NOT invent anything beyond the description.\n"
        "7. Keep the output clean, readable, and logically structured.\n"
    )

    if is_plain:
        lore_text = lore.get("description", "")
        prompt = (
            intro +
            f"\n🔍 QUEST DESCRIPTION:\n{lore_text}\n\n" +
            "🎯 Your output must follow this exact format:\n"
            "=== DOMAIN START ===\n<insert domain.pddl here>\n=== DOMAIN END ===\n"
            "=== PROBLEM START ===\n<insert problem.pddl here>\n=== PROBLEM END ===\n"
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
            "\n📦 OBJECTS:\n" + object_list + "\n\n" +
            "🔋 INITIAL STATE:\n" + initial_state + "\n\n" +
            "🎯 GOAL CONDITIONS:\n" + goal_conditions + "\n\n" +
            f"🔀 BRANCHING FACTOR: min {branching['min']}, max {branching['max']}\n" +
            f"🧭 DEPTH CONSTRAINTS: min {depth['min']}, max {depth['max']}\n\n" +
            f"🗺️ QUEST TITLE: {lore.get('quest_title', '(not provided)')}\n" +
            f"🌍 WORLD CONTEXT: {lore.get('world_context', '(not provided)')}\n" +
            f"📜 NARRATIVE DESCRIPTION:\n{lore.get('description', '')}\n\n" +
            "🎯 Your output MUST follow this format:\n"
            "=== DOMAIN START ===\n<insert domain.pddl here>\n=== DOMAIN END ===\n"
            "=== PROBLEM START ===\n<insert problem.pddl here>\n=== PROBLEM END ===\n"
        )

    if examples_text:
        prompt += "\n📚 REFERENCE EXAMPLES:\n" + examples_text

    return prompt, [f"Example {i+1}" for i in range(len(examples))]




def generate_pddl_from_dict(
    lore: dict,
    lore_path: Optional[str] = None
) -> Tuple[Optional[str], Optional[str], List[str]]:
    prompt, used_examples = build_prompt_from_lore(lore)
    raw = ask_ollama(prompt)

    session_dir = os.path.join(
        "uploads", "tmp" if not lore_path else os.path.basename(lore_path).split(".")[0]
    )
    os.makedirs(session_dir, exist_ok=True)
    save_text_file(os.path.join(session_dir, "raw_llm_response.txt"), raw)

    domain = extract_between(raw, "=== DOMAIN START ===", "=== DOMAIN END ===")
    problem = extract_between(raw, "=== PROBLEM START ===", "=== PROBLEM END ===")

    if not domain or not problem or not domain.strip().lower().startswith("(define"):
        logger.warning("⚠️ Generazione fallita: PDDL non valido.")
        return None, None, used_examples

    validation = validate_pddl(domain, problem, lore)
    if not validation["valid_syntax"]:
        logger.warning("⚠️ Validazione fallita: %s", json.dumps(validation, indent=2))
        save_text_file(
            os.path.join(session_dir, "validation_failed.json"),
            json.dumps(validation, indent=2)
        )
        return None, None, used_examples

    return domain, problem, used_examples


def generate_pddl_from_lore(lore_path: str) -> Tuple[Optional[str], Optional[str], List[str]]:
    lore = load_lore(lore_path)
    return generate_pddl_from_dict(lore, lore_path)
