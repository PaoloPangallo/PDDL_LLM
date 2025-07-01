"""
Modulo per generare i file PDDL da un lore JSON, utilizzando esempi simili e un LLM locale.
"""

import os
import json
import logging
from typing import Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from game.utils import ask_ollama, extract_between, save_text_file
from db.db import retrieve_similar_examples_from_db

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
        sims = cosine_similarity(vec[-1], vec[:-1]).flatten()
        best_index = sims.argmax()
        return [(names[best_index], texts[best_index])]
    except (ValueError, IndexError) as e:
        logger.warning("Errore durante la similarità: %s", e)
        return []


def build_prompt_from_lore(lore: dict, examples: Optional[list[str]] = None) -> tuple[str, list[str]]:
    """Costruisce il prompt da inviare al modello LLM a partire dal lore ed esempi opzionali RAG."""
    lore_text = json.dumps(lore, indent=2)
    examples = examples or []
    examples_text = ""

    for i, content in enumerate(examples):
        if "(define" in content and "(:action" in content:
            examples_text += f"\n// ---- Example {i + 1} ----\n{content.strip()}\n"

    initial_state = "\n".join(lore.get("init", []))
    goal_conditions = "\n".join(lore.get("goal", []))
    object_list = "\n".join(lore.get("objects", []))

    prompt = (
        "You are an expert in PDDL generation for classical planning.\n\n"
        "Your task is to generate exactly **two valid PDDL files**:\n"
        "1. `domain.pddl`\n"
        "2. `problem.pddl`\n\n"
        "⚠️ Follow STRICTLY the PDDL standard syntax. Do NOT invent syntax or wrap blocks incorrectly.\n"
        "⚠️ Every section MUST be included and well-formed.\n\n"

        "🔤 Use exactly the same objects, names and predicates found in the lore.\n"
        "Do not rename or invent entities. These must appear:\n"
        f"{object_list}\n\n"

        "🧠 DOMAIN file format:\n"
        "Must include these required sections:\n"
        "- `(:requirements ...)`\n"
        "- `(:types ...)`\n"
        "- `(:predicates ...)`\n"
        "- At least one `(:action name ...)` — use this exact syntax\n\n"

        "📦 PROBLEM file format:\n"
        "Must include these required sections:\n"
        "- `(:domain ...)`\n"
        "- `(:objects ...)`\n"
        "- `(:init ...)` — use FLAT predicates, NO `(and (...))`\n"
        "- `(:goal ...)`\n\n"

        "🎯 OUTPUT FORMAT:\n"
        "Wrap your answer between these exact delimiters:\n"
        "=== DOMAIN START ===\n<insert full domain.pddl here>\n=== DOMAIN END ===\n"
        "=== PROBLEM START ===\n<insert full problem.pddl here>\n=== PROBLEM END ===\n\n"

        f"📚 Examples (optional):\n{examples_text}"
        f"\n🗺️ QUEST TITLE: {lore.get('quest_title', '')}\n"
        f"🌍 WORLD CONTEXT: {lore.get('world_context', '')}\n"
        f"📜 QUEST DESCRIPTION:\n{lore.get('description', '')}\n"
        f"📦 INITIAL STATE:\n{initial_state}\n"
        f"🎯 GOAL CONDITIONS:\n{goal_conditions}\n"
    )

    return prompt, [f"Example {i + 1}" for i in range(len(examples))]



def generate_pddl_from_lore(lore_path: str) -> tuple[str, str, list[str]]:
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
