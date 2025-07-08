import re
import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

PDDL_SECTIONS = ["(:types", "(:predicates", "(:action", "(:objects", "(:init", "(:goal)"]


def validate_pddl(domain: str, problem: str, lore: Any) -> Dict:
    # Lore può essere stringa o dict
    if isinstance(lore, str):
        try:
            lore_dict = json.loads(lore)
        except json.JSONDecodeError:
            lore_dict = {}
    elif isinstance(lore, dict):
        lore_dict = lore
    else:
        lore_dict = {}

    report = {
        "valid_syntax": True,
        "missing_sections": [],
        "undefined_predicates_in_goal": [],
        "undefined_predicates_in_init": [],
        "undefined_actions": [],
        "mismatched_lore_entities": [],
        "domain_mismatch": None,
        "semantic_errors": []
    }

    # 1. Sezioni obbligatorie
    check_required_sections(domain, problem, report)

    # 2. Nome dominio coerente
    check_domain_name_match(domain, problem, report)

    # 3. Oggetti e goal
    object_list = extract_objects(problem)
    goal_atoms = extract_goal_atoms(problem)
    init_atoms = extract_init_atoms(problem)
    logger.debug("📋 Validating PDDL with %d objects, %d goal atoms", len(object_list), len(goal_atoms))

    # 4. Coerenza con oggetti in goal/init
    report["undefined_predicates_in_goal"] = [
        atom[0] for atom in goal_atoms if atom[0] not in extract_predicates(domain)
    ]
    report["undefined_predicates_in_init"] = [
        atom[0] for atom in init_atoms if atom[0] not in extract_predicates(domain)
    ]

    report["undefined_objects_in_goal"] = [
        obj for atom in goal_atoms for obj in atom[1:] if obj not in object_list
    ]

    # 5. Entità extra nel lore
    lore_entities = []
    if "entities" in lore_dict or "inventory" in lore_dict:
        lore_entities = lore_dict.get("entities", []) + lore_dict.get("inventory", [])
        object_set = set(object_list)
        report["mismatched_lore_entities"] = [e for e in lore_entities if e not in object_set]

    # 6. Azioni
    defined_actions = extract_action_names(domain)
    used_actions = extract_plan_actions(problem)
    report["undefined_actions"] = [a for a in used_actions if a not in defined_actions]

    # 7. Errori semantici
    if isinstance(lore_dict.get("init"), list) and isinstance(lore_dict.get("goal"), list):
        report["semantic_errors"].extend(semantic_check(problem, lore_dict))

    # 8. Struttura azioni
    report["semantic_errors"].extend(validate_action_structure(domain))

    # 9. Invalida se errori
    if (
        report["missing_sections"]
        or report["semantic_errors"]
        or report["undefined_predicates_in_goal"]
        or report["undefined_predicates_in_init"]
    ):
        report["valid_syntax"] = False

    return report


# =======================
# 🔍 Helper functions
# =======================

def check_required_sections(domain: str, problem: str, report: Dict):
    for section in ["(:types", "(:predicates", "(:action"]:
        if section not in domain:
            report["missing_sections"].append(section)
    for section in ["(:objects", "(:init", "(:goal"]:
        if section not in problem:
            report["missing_sections"].append(section)


def check_domain_name_match(domain: str, problem: str, report: Dict):
    domain_decl = re.search(r"\(define\s*\(domain\s+(\w+)\)", domain)
    problem_decl = re.search(r"\(:domain\s+(\w+)\)", problem)
    if domain_decl and problem_decl:
        dom_name = domain_decl.group(1).strip()
        prob_name = problem_decl.group(1).strip()
        if dom_name != prob_name:
            msg = (
                f"❌ Domain mismatch: '{dom_name}' (domain) vs '{prob_name}' (problem). "
                "🛠 Assicurati che il nome sia uguale in entrambi i file."
            )
            report["domain_mismatch"] = msg
            report["semantic_errors"].append(msg)
            report["valid_syntax"] = False


def extract_objects(problem: str) -> List[str]:
    match = re.search(r"\(:objects(.*?)\)", problem, re.DOTALL)
    if not match:
        return []
    tokens = match.group(1).split()
    result, current = [], []
    for t in tokens:
        if t == "-":
            result.extend(current)
            current = []
        elif not t.startswith("-"):
            current.append(t)
    result.extend(current)
    return result


def extract_goal_atoms(problem: str) -> List[List[str]]:
    match = re.search(r"\(:goal\s*(\(.*?\))\s*\)", problem, re.DOTALL)
    if not match:
        return []
    return [atom.split() for atom in re.findall(r"\(([^()]+)\)", match.group(1))]


def extract_init_atoms(problem: str) -> List[List[str]]:
    match = re.search(r"\(:init(.*?)\)\s*\(:goal", problem, re.DOTALL)
    if not match:
        return []
    return [atom.split() for atom in re.findall(r"\(([^()]+)\)", match.group(1))]


def extract_predicates(domain: str) -> List[str]:
    match = re.search(r"\(:predicates(.*?)\)", domain, re.DOTALL)
    if not match:
        return []
    return list(set(re.findall(r"\(([\w-]+)", match.group(1))))



def extract_action_names(domain: str) -> List[str]:
    return re.findall(r"\(:action\s+([\w-]+)", domain)


def extract_plan_actions(problem: str) -> List[str]:
    """
    Dummy estrattore: estrae parole che sembrano azioni dentro :goal (solo per hint).
    """
    actions = set()
    matches = re.findall(r"\(:goal\s*(\(.*?\))\s*\)", problem, re.DOTALL)
    for body in matches:
        for match in re.findall(r"\(([\w-]+)", body):
            if match not in {"and", "or", "not"}:
                actions.add(match)
    return list(actions)



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

    init_actual = ["(" + " ".join(a) + ")" for a in extract_init_atoms(problem)]
    goal_actual = ["(" + " ".join(a) + ")" for a in extract_goal_atoms(problem)]

    for fact in init_expected:
        if fact not in init_actual:
            errors.append(
                f"❌ Init mismatch: '{fact}' not found in problem. "
                f"🛠 Aggiungi questa tupla nella sezione (:init)."
            )
    for fact in goal_expected:
        if fact not in goal_actual:
            errors.append(
                f"❌ Goal mismatch: '{fact}' not found in problem. "
                f"🛠 Aggiungi questa tupla nella sezione (:goal)."
            )
    return errors


def validate_action_structure(domain: str) -> List[str]:
    problems = []
    actions = re.findall(r"\(:action\s+([\w-]+)(.*?)(?=\(:action|\Z)", domain, re.DOTALL)
    for name, block in actions:
        if ":parameters" not in block:
            problems.append(f"❌ Action '{name}' is missing ':parameters'.")
        if ":precondition" not in block:
            problems.append(f"❌ Action '{name}' is missing ':precondition'.")
        if ":effect" not in block:
            problems.append(f"❌ Action '{name}' is missing ':effect'.")
    return problems





