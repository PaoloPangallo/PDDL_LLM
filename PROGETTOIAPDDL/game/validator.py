import re
import logging
from typing import Dict, List, TypedDict

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class ValidationError(TypedDict):
    kind: str
    section: str
    detail: str
    predicate: str | None
    occurrence: str | None
    suggestion: str | None

def validate_pddl(domain: str, problem: str, lore: dict) -> Dict:
    """
    Valida dominio e problema PDDL e restituisce un report strutturato.
    Report contiene:
      - valid_syntax: bool
      - missing_sections: List[str]
      - undefined_objects_in_goal: List[str]
      - undefined_actions: List[str]
      - semantic_errors: List[str]
      - errors: List[ValidationError]
    """
    report = {
        "valid_syntax": True,
        "missing_sections": [],
        "undefined_objects_in_goal": [],
        "undefined_actions": [],
        "semantic_errors": [],
        "errors": []
    }

    # Sezioni obbligatorie
    for sec in ["(:types", "(:predicates", "(:action"]:
        if sec not in domain:
            report["missing_sections"].append(sec)
    for sec in ["(:objects", "(:init", "(:goal"]:
        if sec not in problem:
            report["missing_sections"].append(sec)

    if report["missing_sections"]:
        report["valid_syntax"] = False

    # Oggetti dichiarati
    objects = []
    m_obj = re.search(r"\(:objects(.*?)\)", problem, re.DOTALL)
    if m_obj:
        tokens = m_obj.group(1).split()
        objects = [t for t in tokens if t != "-" and not tokens[tokens.index(t)-1] == "-"]
    else:
        report["errors"].append({
            "kind": "missing_section",
            "section": ":objects",
            "detail": "Objects section is missing",
            "predicate": None,
            "occurrence": None,
            "suggestion": "Add (:objects ...) section"
        })

    # Init
    init_atoms = []
    m_init = re.search(r"\(:init(.*?)\)\s*(?:\(:goal|\Z)", problem, re.DOTALL)
    if m_init:
        init_atoms = re.findall(r"\(([^()]+)\)", m_init.group(1))
    else:
        report["errors"].append({
            "kind": "missing_section",
            "section": ":init",
            "detail": "Init section is missing",
            "predicate": None,
            "occurrence": None,
            "suggestion": "Add (:init ...) section"
        })

    # Goal
    goal_atoms = []
    m_goal = re.search(r"\(:goal\s*(\(.*?\))\s*\)", problem, re.DOTALL)
    if m_goal:
        goal_atoms = re.findall(r"\(([^()]+)\)", m_goal.group(1))
    else:
        report["errors"].append({
            "kind": "missing_section",
            "section": ":goal",
            "detail": "Goal section is missing",
            "predicate": None,
            "occurrence": None,
            "suggestion": "Add (:goal ...) section"
        })

    # Confronto semantico con la lore
    for fact in lore.get("init", []):
        if fact.strip("()") not in [atom.strip() for atom in init_atoms]:
            report["semantic_errors"].append(f"Init missing: {fact}")
    for fact in lore.get("goal", []):
        if fact.strip("()") not in [atom.strip() for atom in goal_atoms]:
            report["semantic_errors"].append(f"Goal missing: {fact}")

    # Oggetti usati nei goal
    for atom in goal_atoms:
        parts = atom.split()
        for arg in parts[1:]:
            if arg not in objects:
                report["undefined_objects_in_goal"].append(arg)

    # Azioni definite
    defined_actions = re.findall(r"\(:action\s+([\w-]+)", domain)

    # Azioni usate (se c'è un piano)
    used_actions = []
    if "(:plan" in problem:
        used_actions = re.findall(r"\b(" + "|".join(defined_actions) + r")\b", problem)
    report["undefined_actions"] = [a for a in used_actions if a not in defined_actions]

    # Firme dei predicati
    preds = {}
    m_preds = re.search(r"\(:predicates(.*?)\)", domain, re.DOTALL)
    if m_preds:
        for decl in re.findall(r"\((\w+)([^)]*)\)", m_preds.group(1)):
            name, rest = decl
            preds[name] = len(re.findall(r"\?\w+", rest))

    all_atoms = [(":init", init_atoms), (":goal", goal_atoms)]
    for section, atoms in all_atoms:
        for atom in atoms:
            parts = atom.strip().split()
            name, args = parts[0], parts[1:]
            if name not in preds:
                report["errors"].append({
                    "kind": "undeclared_predicate",
                    "section": section,
                    "detail": f"Predicate '{name}' not declared in (:predicates)",
                    "predicate": name,
                    "occurrence": f"({atom})",
                    "suggestion": f"Add predicate declaration: ({name} ...) in (:predicates)"
                })
            elif len(args) != preds[name]:
                report["errors"].append({
                    "kind": "arity_mismatch",
                    "section": section,
                    "detail": f"{name} expects {preds[name]} args, got {len(args)}",
                    "predicate": name,
                    "occurrence": f"({atom})",
                    "suggestion": f"Update ({atom}) to match predicate arity or fix its definition"
                })

    if (report["errors"]
        or report["semantic_errors"]
        or report["undefined_objects_in_goal"]
        or report["undefined_actions"]):
        report["valid_syntax"] = False

    return report