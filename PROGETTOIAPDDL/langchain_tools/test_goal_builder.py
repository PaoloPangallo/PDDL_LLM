# langchain_tools/test_goal_builder.py

from langchain_tools.quest_goal import QuestGoal
from langchain_tools.goal_builder import generate_goal_block

goal = QuestGoal(
    destination="Tower of Varnak",
    required_item="Sword of Fire",
    success_condition="defeat the Ice Dragon"
)

goal_block = generate_goal_block(goal)

print("🧾 Goal Block PDDL:")
print(goal_block)
