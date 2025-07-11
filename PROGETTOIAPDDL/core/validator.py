import re
import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

PDDL_SECTIONS = ["(:types", "(:predicates", "(:action", "(:objects", "(:init", "(:goal)"]

def validate_pddl(domain: str, problem: str, lore: Any) -> Dict:
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
        "undefined_objects_in_goal": [],
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

    predicates = extract_predicates(domain)

    report["undefined_predicates_in_goal"] = [
        atom[0] for atom in goal_atoms if atom[0] not in predicates
    ]
    report["undefined_predicates_in_init"] = [
        atom[0] for atom in init_atoms if atom[0] not in predicates
    ]

    report["undefined_objects_in_goal"] = [
        obj for atom in goal_atoms for obj in atom[1:] if obj not in object_list
    ]

    # 4. Entità extra nel lore
    lore_entities = lore_dict.get("entities", []) + lore_dict.get("inventory", [])
    object_set = set(object_list)
    report["mismatched_lore_entities"] = [e for e in lore_entities if e not in object_set]

    # 5. Verifica semantica con init/goal
    if isinstance(lore_dict.get("init"), list) and isinstance(lore_dict.get("goal"), list):
        report["semantic_errors"].extend(semantic_check(problem, lore_dict))

    # 6. Controlli sintattici e semantici sul dominio
    report["semantic_errors"].extend(validate_action_structure(domain))
    report["semantic_errors"].extend(detect_invalid_predicate_syntax(domain))
    report["semantic_errors"].extend(validate_parameter_typing(domain))
    report["semantic_errors"].extend(detect_hardcoded_constants(domain, object_list))

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

def semantic_check(problem: str, lore: dict) -> List[str]:
    errors = []
    init_expected = lore.get("init", [])
    goal_expected = lore.get("goal", [])

    init_actual = ["(" + " ".join(a) + ")" for a in extract_init_atoms(problem)]
    goal_actual = ["(" + " ".join(a) + ")" for a in extract_goal_atoms(problem)]

    for fact in init_expected:
        if fact not in init_actual:
            errors.append(f"❌ Init mismatch: '{fact}' not found in problem. 🛠 Aggiungi questa tupla nella sezione (:init).")
    for fact in goal_expected:
        if fact not in goal_actual:
            errors.append(f"❌ Goal mismatch: '{fact}' not found in problem. 🛠 Aggiungi questa tupla nella sezione (:goal).")
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

def detect_invalid_predicate_syntax(domain: str) -> List[str]:
    errors = []
    match = re.search(r"\(:predicates(.*?)\)", domain, re.DOTALL)
    if not match:
        return errors
    block = match.group(1)
    for line in block.split("\n"):
        if "-" in line and not re.search(r"\?\w+\s+-\s+\w+", line):
            errors.append(f"❌ Invalid predicate syntax: `{line.strip()}` — expected typed parameters.")
    return errors

def validate_parameter_typing(domain: str) -> List[str]:
    errors = []
    matches = re.findall(r":parameters\s*\((.*?)\)", domain, re.DOTALL)
    for param_block in matches:
        tokens = param_block.split()
        for i, token in enumerate(tokens):
            if token.startswith("?") and (i+1 >= len(tokens) or tokens[i+1] != "-"):
                errors.append(f"❌ Parameter `{token}` is missing type declaration.")
    return errors

def detect_hardcoded_constants(domain: str, object_names: List[str]) -> List[str]:
    errors = []
    for obj in object_names:
        if re.search(rf"\b{re.escape(obj)}\b", domain):
            errors.append(f"⚠️ Object '{obj}' appears directly in the domain. Use typed parameters instead.")
    return errors
