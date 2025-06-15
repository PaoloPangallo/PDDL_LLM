# pylint: disable=missing-docstring,line-too-long,broad-except,unspecified-encoding


import re
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

PDDL_SECTIONS = ["(:types", "(:predicates", "(:action", "(:objects", "(:init", "(:goal"]

def validate_pddl(domain: str, problem: str, lore: dict) -> Dict:
    report = {
        "valid_syntax": True,
        "missing_sections": [],
        "undefined_objects_in_goal": [],
        "undefined_actions": [],
        "mismatched_lore_entities": []
    }

    # === 1. Check essential PDDL sections ===
    for section in ["(:types", "(:predicates", "(:action"]:
        if section not in domain:
            report["missing_sections"].append(section)
            report["valid_syntax"] = False

    for section in ["(:objects", "(:init", "(:goal"]:
        if section not in problem:
            report["missing_sections"].append(section)
            report["valid_syntax"] = False

    # === 2. Extract objects and goal entities ===
    object_list = extract_objects(problem)
    goal_atoms = extract_goal_atoms(problem)

    undefined_objects = [obj for atom in goal_atoms for obj in atom if obj not in object_list]
    report["undefined_objects_in_goal"] = undefined_objects

    # === 3. Check if lore entities match objects ===
    lore_entities = lore.get("entities", []) + lore.get("inventory", [])
    mismatches = [e for e in lore_entities if e not in object_list]
    report["mismatched_lore_entities"] = mismatches

    # === 4. Placeholder for undefined actions check ===
    # TODO: Parse actions and check usage in plan steps
    # report["undefined_actions"] = [...]

    return report

def extract_objects(problem: str) -> List[str]:
    match = re.search(r"\(:objects(.*?)\)", problem, re.DOTALL)
    if not match:
        return []
    content = match.group(1)
    tokens = content.split()
    return [t for t in tokens if not t.startswith("-")]

def extract_goal_atoms(problem: str) -> List[List[str]]:
    match = re.search(r"\(:goal\s*\(and(.*?)\)\s*\)", problem, re.DOTALL)
    if not match:
        return []
    content = match.group(1)
    atoms = re.findall(r"\(([^()]+)\)", content)
    return [atom.split() for atom in atoms]

if __name__ == "__main__":
    import json
    with open("uploads/lore-generated/domain.pddl", "r") as f:
        domain = f.read()
    with open("uploads/lore-generated/problem.pddl", "r") as f:
        problem = f.read()
    with open("lore/example_lore.json", "r") as f:
        lore = json.load(f)

    result = validate_pddl(domain, problem, lore)
    print(json.dumps(result, indent=2))