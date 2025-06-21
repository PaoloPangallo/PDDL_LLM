# langchain_tools/goal_builder.py

from langchain_tools.quest_goal import QuestGoal
import re

def normalize_name(text: str) -> str:
    """Converte nomi umani in identificatori PDDL validi"""
    return re.sub(r"[^a-z0-9\-]", "-", text.strip().lower().replace(" ", "-"))

def generate_goal_block(goal: QuestGoal) -> str:
    """Genera il blocco (:goal ...) PDDL da un QuestGoal strutturato"""
    destination = normalize_name(goal.destination)
    item = normalize_name(goal.required_item)
    condition = goal.success_condition.strip().lower()

    # Heuristic basic mappings for success_condition → predicate
    condition_predicate = ""
    if "defeat" in condition or "kill" in condition:
        target = normalize_name(re.sub(r"(defeat|kill|the)", "", condition).strip())
        condition_predicate = f"(defeated {target})"
    elif "rescue" in condition:
        target = normalize_name(re.sub(r"(rescue|the)", "", condition).strip())
        condition_predicate = f"(rescued {target})"
    else:
        # fallback
        condition_predicate = f"; unknown goal: {goal.success_condition}"

    return f"""(:goal
  (and
    (at hero {destination})
    (has hero {item})
    {condition_predicate}
  )
)"""
