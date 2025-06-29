"""Modulo per la generazione automatica di file PDDL da un documento di lore."""

import os
import json
import logging
from game.utils import ask_ollama, extract_between, save_text_file
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Optional


logger = logging.getLogger(__name__)

def load_lore(lore_path: str) -> dict:
    """Carica il file di lore JSON dal percorso fornito."""
    with open(lore_path, encoding="utf-8") as f:
        return json.load(f)

def load_pddl_examples(max_examples=5) -> list[tuple[str, str]]:
    """
    Carica esempi PDDL da sottocartelle di 'pddl_examples'.

    Ritorna una lista di tuple (nome_cartella, contenuto_pddl_combinato).
    """
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
    """
    Recupera l'esempio PDDL più simile al testo del lore.

    Utilizza TF-IDF + similarità coseno tra lore e esempi PDDL.
    """
    examples = load_pddl_examples(max_examples=3)
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

def build_prompt_from_lore(lore: dict) -> tuple[str, list[str]]:
    """
    Costruisce il prompt da inviare al modello LLM a partire dal lore e da esempi simili.

    Restituisce il prompt completo e i nomi degli esempi utilizzati.
    """
    lore_text = json.dumps(lore, indent=2)
    examples = retrieve_best_example(lore_text)

    examples_text = ""
    for name, content in examples:
        if "(define" in content and "(:action" in content:
            examples_text += f"\n// ---- {name} ----\n{content.strip()}\n"

    initial_state = "\n".join(lore.get("initial_state", []))
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

    "Wrap your output exactly between these markers:\n"
    "=== DOMAIN START ===\n"
    "<domain.pddl here>\n"
    "=== DOMAIN END ===\n"
    "=== PROBLEM START ===\n"
    "<problem.pddl here>\n"
    "=== PROBLEM END ===\n"
    f"\nRelevant Examples:\n{examples_text}"
    f"\nQUEST TITLE: {lore.get('quest_title', '')}\n"
    f"WORLD CONTEXT: {lore.get('world_context', '')}\n"
    f"INITIAL STATE:\n{initial_state}\n"
    f"GOAL CONDITIONS:\n{goal_conditions}\n"
)


    used_example_names = [name for name, _ in examples]
    return prompt, used_example_names

def generate_pddl_from_lore(lore_path: str) -> tuple[str, str, list[str]]:
    """
    Genera i file PDDL a partire da un file JSON di lore.

    Restituisce: (domain.pddl, problem.pddl, nomi_esempi_usati)
    """
    lore = load_lore(lore_path)
    return generate_pddl_from_dict(lore, lore_path)

def generate_pddl_from_dict(lore: dict, lore_path: str = None) -> tuple[Optional[str], Optional[str], list[str]]:
    """
    Genera i file PDDL a partire da un dizionario di lore.

    Se fornito, salva anche l'output raw dell'LLM.

    Ritorna (domain, problem, esempi) oppure (None, None, esempi) se fallisce.
    """
    prompt, used_examples = build_prompt_from_lore(lore)
    raw = ask_ollama(prompt)

    if lore_path:
        session_dir = os.path.join("uploads", os.path.basename(lore_path).split(".")[0])
        os.makedirs(session_dir, exist_ok=True)
        save_text_file(os.path.join(session_dir, "raw_llm_response.txt"), raw)

    domain = extract_between(raw, "=== DOMAIN START ===", "=== DOMAIN END ===")
    problem = extract_between(raw, "=== PROBLEM START ===", "=== PROBLEM END ===")

    # ✅ NON lanciare errore, ma restituisci None
    if not domain or not problem or not domain.strip().lower().startswith("(define"):
        logger.warning("⚠️ Generazione fallita: PDDL non valido.")
        return None, None, used_examples

    return domain, problem, used_examples
