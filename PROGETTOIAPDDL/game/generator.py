# pylint: disable=missing-docstring,line-too-long,broad-except,unspecified-encoding


import os
import json
import logging
from game.utils import ask_ollama, extract_between, save_text_file
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer



logger = logging.getLogger(__name__)


def load_lore(lore_path: str) -> dict:
    with open(lore_path, encoding="utf-8") as f:
        return json.load(f)


import json

def build_prompt_from_lore(lore: dict) -> tuple[str, list[str]]:
    lore_text = json.dumps(lore, indent=2)
    examples = retrieve_best_examples(lore_text)

    # Costruzione sezione esempi
    examples_text = "\n📚 Here are some similar examples:\n"
    for name, content in examples:
        examples_text += f"\n// ---- {name} ----\n{content}\n"

    # Prompt completo
    prompt = (
        "🎯 You are a professional PDDL generator for classical planners like Fast Downward.\n\n"
        "👉 Your task is to generate exactly two valid PDDL files: `domain.pddl` and `problem.pddl`.\n"
        "You MUST use only standard PDDL syntax. Wrap your output between the specified delimiters. Do not include anything else.\n\n"
        "🧱 RULES:\n"
        "- Do NOT include any explanations or comments outside the PDDL blocks.\n"
        "- Do NOT use non-standard LISP syntax, pseudo-code, or conditional logic like `if`, `find-distance`, or perception predicates.\n"
        "- Use only these standard PDDL sections: `(:requirements)`, `(:types)`, `(:predicates)`, `(:action ...)`, `(:objects)`, `(:init)`, `(:goal)`.\n\n"
        "✅ DOMAIN must contain:\n"
        "- (define (domain <name>))\n"
        "- (:requirements :strips [:typing])\n"
        "- (:types ...)\n"
        "- (:predicates ...)\n"
        "- At least 2-3 actions with `:parameters`, `:precondition`, and `:effect`\n\n"
        "✅ PROBLEM must contain:\n"
        "- (define (problem <name>))\n"
        "- (domain <name>)\n"
        "- (:objects ...)\n"
        "- (:init ...)\n"
        "- (:goal (and ...))\n\n"
        "🚫 Forbidden constructs: `if`, nested effects, DSL-style definitions, perception, `stream` predicates, or comments.\n\n"
        "✂️ Return ONLY the following blocks:\n"
        "=== DOMAIN START ===\n<domain.pddl here>\n=== DOMAIN END ===\n"
        "=== PROBLEM START ===\n<problem.pddl here>\n=== PROBLEM END ===\n\n"
        + examples_text +
        "\n📘 QUEST TITLE: {title}\n"
        "🌍 WORLD CONTEXT: {context}\n"
        "🔛 INITIAL STATE:\n{initial}\n"
        "🎯 GOAL CONDITIONS:\n{goal}\n"
        "🌱 BRANCHING FACTOR: {branching}\n"
        "📏 DEPTH CONSTRAINTS: {depth}\n"
    ).format(
        title=lore.get("quest_title", ""),
        context=lore.get("world_context", ""),
        initial="\n".join(lore.get("initial_state", [])),
        goal="\n".join(lore.get("goal", [])),
        branching=lore.get("branching_factor", ""),
        depth=lore.get("depth_constraints", "")
    )

    used_example_names = [name for name, _ in examples]
    return prompt, used_example_names












def generate_pddl_from_lore(lore_path: str) -> tuple[str, str, list[str]]:
    lore = load_lore(lore_path)
    return generate_pddl_from_dict(lore, lore_path)



def generate_pddl_from_dict(lore: dict, lore_path: str = None) -> tuple[str, str, list[str]]:
    prompt, used_example_names = build_prompt_from_lore(lore)

    raw = ask_ollama(prompt)

    if lore_path:
        session_dir = os.path.join("uploads", os.path.basename(lore_path).split(".")[0])
        os.makedirs(session_dir, exist_ok=True)
        save_text_file(os.path.join(session_dir, "raw_llm_response.txt"), raw)

    domain = extract_between(raw, "=== DOMAIN START ===", "=== DOMAIN END ===")
    problem = extract_between(raw, "=== PROBLEM START ===", "=== PROBLEM END ===")

    if not domain or not problem:
        logger.error("❌ DOMINIO o PROBLEMA non trovati nella risposta.")
        raise ValueError("Blocco DOMAIN o PROBLEM mancante.")

    if not domain.lower().startswith("(define") or not problem.lower().startswith("(define"):
        logger.error("❌ I file PDDL non iniziano con (define)")
        raise ValueError("I file PDDL non iniziano correttamente con (define).")

    return domain, problem, used_example_names



def load_pddl_examples(base_path="pddl_examples") -> list[tuple[str, str]]:
    examples = []
    for subfolder in os.listdir(base_path):
        folder_path = os.path.join(base_path, subfolder)
        domain_path = os.path.join(folder_path, "domain.pddl")
        problem_path = os.path.join(folder_path, "problem.pddl")

        if os.path.isfile(domain_path) and os.path.isfile(problem_path):
            with open(domain_path, encoding="utf-8") as f1, open(problem_path, encoding="utf-8") as f2:
                content = f"// Example: {subfolder}\n\n" + f1.read() + "\n" + f2.read()
                examples.append((subfolder, content))
    return examples




def retrieve_best_examples(lore_text: str, top_k=2):
    examples = load_pddl_examples()
    texts = [ex[1] for ex in examples]
    names = [ex[0] for ex in examples]

    vectorizer = TfidfVectorizer().fit_transform(texts + [lore_text])
    similarities = cosine_similarity(vectorizer[-1], vectorizer[:-1]).flatten()
    top_indices = similarities.argsort()[-top_k:][::-1]

    return [(names[i], texts[i]) for i in top_indices]

