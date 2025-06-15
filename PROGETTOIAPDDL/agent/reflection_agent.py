import os
import requests
import logging
from game.validator import validate_pddl
from game.utils import read_text_file, save_text_file
from game.utils import extract_between



OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
DEFAULT_MODEL = "mistral"
HEADERS = {"Content-Type": "application/json"}

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def ask_local_llm(prompt: str, model: str = DEFAULT_MODEL) -> str:
    logger.info("🤖 Invio richiesta a Ollama...")
    logger.debug(f"📤 Prompt inviato:\n{prompt}")
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": model, "prompt": prompt, "stream": False},
            headers=HEADERS,
            timeout=(10, 360)
        )
        resp.raise_for_status()
        data = resp.json()
        answer = data.get("response", "").strip()
        if not answer:
            logger.warning("⚠️ Nessuna risposta generata dall'LLM.")
        return answer
    except Exception as e:
        logger.error(f"❌ Errore nella richiesta a Ollama: {e}")
        raise

def build_prompt(domain: str, problem: str, error_message: str, validation: dict = None) -> str:
    diagnostic_text = f"\n\n🩺 Semantic validation summary:\n{json.dumps(validation, indent=2)}" if validation else ""

    return (
        "🎯 You are a PDDL expert for classical planners like Fast Downward.\n\n"
        "You are given two PDDL files (`domain.pddl` and `problem.pddl`) that produce no valid plan.\n"
        f"The planner returned the following error:\n\n{error_message}\n"
        f"{diagnostic_text}\n\n"
        "🧩 Your task is to revise the PDDL code so that the planner finds a valid plan.\n"
        "Make sure that:\n"
        "- Every predicate used in the goal is correctly defined in the domain.\n"
        "- All object types are declared if used.\n"
        "- All actions needed to satisfy the goal are reachable and have valid preconditions.\n\n"
        "🔧 Return **only** updated content (domain and/or problem), formatted within these delimiters:\n"
        "=== DOMAIN START ===\n...your domain content...\n=== DOMAIN END ===\n"
        "=== PROBLEM START ===\n...your problem content...\n=== PROBLEM END ===\n\n"
        "Do not add explanations or comments outside the PDDL code.\n\n"
        f"🗂️ DOMAIN:\n{domain}\n\n"
        f"📄 PROBLEM:\n{problem}"
    )



def refine_pddl(domain_path: str, problem_path: str, error_message: str, lore: dict = None, model: str = DEFAULT_MODEL) -> str:
    domain = read_text_file(domain_path)
    problem = read_text_file(problem_path)
    if not domain or not problem:
        raise ValueError("❌ I file domain.pddl o problem.pddl sono vuoti o mancanti.")

    validation = validate_pddl(domain, problem, lore) if lore else None
    prompt = build_prompt(domain, problem, error_message, validation)
    return ask_local_llm(prompt, model)


def refine_and_save(domain_path: str, problem_path: str, error_message: str, output_dir: str, lore: dict = None):
    suggestion_raw = refine_pddl(domain_path, problem_path, error_message, lore)

    domain_suggestion = extract_between(suggestion_raw, "=== DOMAIN START ===", "=== DOMAIN END ===")
    problem_suggestion = extract_between(suggestion_raw, "=== PROBLEM START ===", "=== PROBLEM END ===")

    if not domain_suggestion:
        raise ValueError("❌ DOMAIN block not found.")
    if not domain_suggestion.strip().lower().startswith("(define"):
        raise ValueError("❌ DOMAIN does not start with (define)")

    # Save suggestions
    os.makedirs(output_dir, exist_ok=True)
    save_text_file(os.path.join(output_dir, "llm_suggestion.pddl"), domain_suggestion.strip())

    if problem_suggestion and problem_suggestion.strip().lower().startswith("(define"):
        save_text_file(os.path.join(output_dir, "llm_problem_suggestion.pddl"), problem_suggestion.strip())

    logger.info(f"✅ Suggestions saved in {output_dir}")
    return domain_suggestion, problem_suggestion


if __name__ == "__main__":
    test_domain = "planner/test_plans/broken_domain.pddl"
    test_problem = "planner/test_plans/problem.pddl"
    test_error = "Fast Downward: nessun piano trovato - azione 'move' irrealizzabile"

    print("🧠 Richiedo suggerimento all'LLM...\n")
    try:
        refined = refine_pddl(test_domain, test_problem, test_error)
        print("✅ Suggerimento LLM:\n")
        print(refined)
    except Exception as e:
        print(f"❌ Errore: {e}")
