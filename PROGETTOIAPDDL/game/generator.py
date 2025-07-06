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


def build_prompt_from_lore(lore: dict, examples: Optional[list[str]] = None) -> tuple[str, list[str]]:
    """Costruisce il prompt da inviare al modello LLM a partire dal lore ed esempi opzionali RAG."""
    lore_text = json.dumps(lore, indent=2)
    examples = examples or []
    examples_text = ""

    for i, content in enumerate(examples):
        if "(define" in content and "(:action" in content:
            examples_text += f"\n// ---- Example {i + 1} ----\n{content.strip()}\n"

    #print("\n\n")
    #print("Esempi caricati:")
    #for i, example in enumerate(examples):
    #    print(f"Example {i + 1}: {example[0]}\n")
    #print("\n\n")

    initial_state = "\n".join(lore.get("init", []))
    goal_conditions = "\n".join(lore.get("goal", []))

    prompt = (
        "You are a professional PDDL generator for classical planners like Fast Downward.\n\n"
        "Your task is to generate exactly two valid PDDL files: `domain.pddl` and `problem.pddl`.\n"
        "⚠️ Use ONLY **standard PDDL syntax** — do NOT include any pseudocode, LISP-like constructs, or comments.\n\n"
        "❌ DO NOT use constructs like: `if`, `eql`, `conjunct`, `let`, `lambda`, `case`, `when`, `either`, `imply`, `cond`.\n"
        "✅ ALLOWED constructs are:\n"
        "- `:requirements`, `:types`, `:predicates`, `:action`\n"
        "- Inside actions: `:parameters`, `:precondition`, `:effect`\n"
        "- Logical expressions: `and`, `not`\n\n"
        "📝 Your DOMAIN file must:\n"
        "- Start with (define (domain ...))\n"
        "- Include (:requirements), (:types), (:predicates), and at least one (:action)\n"
        "- Each action must contain :parameters, :precondition, and :effect only.\n\n"
        "🗂️ Your PROBLEM file must:\n"
        "- Start with (define (problem ...))\n"
        "- Include (:domain ...), (:objects ...), (:init ...), and (:goal ...)\n"
        "- Use flat predicates in (:init ...), not wrapped in (and ...)\n"
        "- Every object in :init and :goal must be declared in :objects\n\n"
        "For example, you can use this generic structure as a basis to generate the required domain and problem.\n\n"
        "=== DOMAIN START ===\n"
        "(define (domain domain_name)\n"
        "  (:requirements :strips :typing)\n"
        "  (:types agent object location)\n"
        "  (:predicates\n"
        "    (at ?x - object ?loc - location)\n"
        "    (has ?a - agent ?o - object))\n"
        "  (:action move\n"
        "    :parameters (?r - agent ?from - location ?to - location)\n"
        "    :precondition (at ?r ?from)\n"
        "    :effect (and (not (at ?r ?from)) (at ?r ?to)))\n"
        "  (:action pickup\n"
        "    :parameters (?r - agent ?p - object ?loc - location)\n"
        "    :precondition (and (at ?r ?loc) (at ?p ?loc))\n"
        "    :effect (has ?r ?p)))\n"
        "=== DOMAIN END ===\n"
        "=== PROBLEM START ===\n"
        "(define (problem problema_name)\n"
        "  (:domain domain_name)\n"
        "  (:objects agent1 - agent\n"
        "            obj1 - object\n"
        "            loc1 loc2 - location)\n"
        "  (:init (at agent1 loc1)\n"
        "         (at obj1 loc1))\n"
        "  (:goal (and (at agent1 loc2)\n"
        "              (has agent1 obj1))))\n"
        "=== PROBLEM END ===\n"
        "\n📘 Lore Constraints:\n"
        "- Use only the **objects**, **initial conditions**, and **goal facts** provided.\n"
        "- Do NOT invent new objects, locations, agents, or actions.\n"
        "- All predicates and logic must be strictly derived from the provided lore.\n"
        "- The story must be faithfully modeled using only the elements described.\n"    
        f"\nQUEST DESCRIPTION:\n{lore.get('description', '')}\n"
        f"INITIAL STATE:\n{initial_state}\n"
        f"GOAL CONDITIONS:\n{goal_conditions}\n"
    )


    return prompt, [f"Example {i + 1}" for i in range(len(examples))]



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