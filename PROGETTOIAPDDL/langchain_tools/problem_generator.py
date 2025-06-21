# langchain_tools/problem_generator.py

from langchain_tools.quest_goal import parse_goal_from_text
from langchain_tools.goal_builder import generate_goal_block, normalize_name
from typing import List

def generate_problem_pddl(
    narrative_goal: str,
    object_declarations: List[str],
    init_facts: List[str],
    problem_name: str = "auto-problem",
    domain_name: str = "auto-domain"
) -> str:
    """
    Genera un file problem.pddl da descrizione narrativa, oggetti e fatti iniziali.
    """
    # Estrai il goal strutturato dalla frase
    structured_goal = parse_goal_from_text(narrative_goal)

    # Costruisci il blocco (:goal ...)
    goal_block = generate_goal_block(structured_goal)

    # Formatta gli oggetti
    objects_block = "  " + "\n  ".join(object_declarations)

    # Formatta i fatti iniziali
    init_block = "    " + "\n    ".join(init_facts)

    # Costruisci il file completo
    return f"""(define (problem {normalize_name(problem_name)})

  (:domain {normalize_name(domain_name)})

  (:objects
{objects_block}
  )

  (:init
{init_block}
  )

  {goal_block}
)
"""
