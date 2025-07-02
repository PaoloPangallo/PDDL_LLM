"""Modulo per la validazione sintattico-semantica dei file PDDL rispetto al lore."""

# pylint: disable=missing-docstring,line-too-long,broad-except,unspecified-encoding

import re
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

PDDL_SECTIONS = ["(:types", "(:predicates", "(:action", "(:objects", "(:init", "(:goal"]


def validate_pddl(domain: str, problem: str, lore: dict) -> Dict:
    """Valida la correttezza dei file domain/problem PDDL in base al contenuto del lore."""
    report = {
        "valid_syntax": True,
        "missing_sections": [],
        "undefined_objects_in_goal": [],
        "undefined_actions": [],
        "mismatched_lore_entities": [],
        "semantic_errors": []
    }

    # 1. Verifica sezioni obbligatorie
    check_required_sections(domain, problem, report)

    # 2. Estrazione oggetti e goal
    object_list = extract_objects(problem)
    goal_atoms = extract_goal_atoms(problem)

    logger.debug("📋 Validating PDDL with %d objects, %d goal atoms", len(object_list), len(goal_atoms))

    report["undefined_objects_in_goal"] = [
        obj for atom in goal_atoms for obj in atom if obj not in object_list
    ]

    # 3. Confronto con entità del lore
    lore_entities = lore.get("entities", []) + lore.get("inventory", [])
    object_set = set(object_list)
    report["mismatched_lore_entities"] = [
        e for e in lore_entities if e not in object_set
    ]

    # 4. Controllo coerenza azioni
    defined_actions = extract_action_names(domain)
    used_actions = extract_plan_actions(problem)  # Dummy for ora
    report["undefined_actions"] = [a for a in used_actions if a not in defined_actions]

    # 5. Validazione semantica coerente con init e goal della lore
    report["semantic_errors"] = semantic_check(problem, lore)

    # 6. Validazione struttura azioni
    report["semantic_errors"].extend(validate_action_structure(domain))

    return report


# =======================
# 🔍 Helper Functions
# =======================

def check_required_sections(domain: str, problem: str, report: Dict):
    required_domain_sections = ["(:types", "(:predicates", "(:action"]
    required_problem_sections = ["(:objects", "(:init", "(:goal"]

    for section in required_domain_sections:
        if section not in domain:
            report["missing_sections"].append(section)
            report["valid_syntax"] = False

    for section in required_problem_sections:
        if section not in problem:
            report["missing_sections"].append(section)
            report["valid_syntax"] = False


def extract_objects(problem: str) -> List[str]:
    """Estrae gli oggetti dichiarati nella sezione :objects del problem."""
    match = re.search(r"\(:objects(.*?)\)", problem, re.DOTALL)
    if not match:
        return []
    content = match.group(1)
    tokens = content.split()
    result = []
    for i, token in enumerate(tokens):
        if token == "-":
            continue
        if i + 1 < len(tokens) and tokens[i + 1] == "-":
            result.append(token)
    return result


def extract_goal_atoms(problem: str) -> List[List[str]]:
    """Estrae gli atomi obiettivo dalla sezione :goal del file problem.pddl."""
    match = re.search(r"\(:goal\s*(\(.*?\))\s*\)", problem, re.DOTALL)
    if not match:
        return []
    atoms = re.findall(r"\(([^()]+)\)", match.group(1))
    return [atom.split() for atom in atoms]


def extract_action_names(domain: str) -> List[str]:
    """Estrae i nomi delle azioni definite nel domain."""
    return re.findall(r"\(:action\s+([\w-]+)", domain)


def extract_plan_actions(problem: str) -> List[str]:
    """Estrae i nomi delle azioni usate nel piano (dummy per ora)."""
    return []


def extract_init_facts(problem: str) -> List[str]:
    match = re.search(r"\(:init(.*?)\)\s*\(:goal", problem, re.DOTALL)
    if not match:
        return []
    atoms = re.findall(r"\(([^()]+)\)", match.group(1))
    return ["(" + a.strip() + ")" for a in atoms]


def extract_goal_facts(problem: str) -> List[str]:
    match = re.search(r"\(:goal\s*(\(.*?\))\s*\)", problem, re.DOTALL)
    if not match:
        return []
    atoms = re.findall(r"\(([^()]+)\)", match.group(1))
    return ["(" + a.strip() + ")" for a in atoms]


def semantic_check(problem: str, lore: dict) -> List[str]:
    errors = []
    init_expected = lore.get("init", [])
    goal_expected = lore.get("goal", [])

    init_actual = extract_init_facts(problem)
    goal_actual = extract_goal_facts(problem)

    for fact in init_expected:
        if fact not in init_actual:
            errors.append(f"❌ Init mismatch: expected '{fact}' not found in problem.")

    for fact in goal_expected:
        if fact not in goal_actual:
            errors.append(f"❌ Goal mismatch: expected '{fact}' not found in problem.")

    return errors


def validate_action_structure(domain: str) -> List[str]:
    """Verifica che ogni azione contenga parametri, precondizioni ed effetti."""
    problems = []
    # Trova tutte le azioni nel dominio, anche se su più righe
    actions = re.findall(r"\(:action\s+([\w-]+)(.*?)(?=\(:action|\Z)", domain, re.DOTALL)
    for name, block in actions:
        if ":parameters" not in block:
            problems.append(f"❌ Action '{name}' is missing ':parameters'.")
        if ":precondition" not in block:
            problems.append(f"❌ Action '{name}' is missing ':precondition'.")
        if ":effect" not in block:
            problems.append(f"❌ Action '{name}' is missing ':effect'.")
    return problems


# =======================
# ✅ Test locale
# =======================

if __name__ == "__main__":
    import json
    with open("uploads/lore-generated/domain.pddl", "r") as f:
        domain_content = f.read()
    with open("uploads/lore-generated/problem.pddl", "r") as f:
        problem_content = f.read()
    with open("lore/example_lore.json", "r") as f:
        lore_data = json.load(f)

    result = validate_pddl(domain_content, problem_content, lore_data)
    print(json.dumps(result, indent=2, ensure_ascii=False))
