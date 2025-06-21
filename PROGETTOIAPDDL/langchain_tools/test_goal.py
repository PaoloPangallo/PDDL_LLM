# langchain_tools/test_goal.py

from langchain_tools.quest_goal import parse_goal_from_text

narrative = (
    "The hero must reach the Tower of Varnak while carrying the Sword of Fire, "
    "and defeat the Ice Dragon who guards the crystal."
)

goal = parse_goal_from_text(narrative)

print("✅ Parsed Goal Object:")
print(goal)
print("🧾 As Dict:", goal.model_dump())
