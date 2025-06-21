import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # aggiunge la cartella sopra

from langchain_tools.quest_description import generate_quest_description


desc = generate_quest_description(
    goal="retrieve the ancient sword",
    obstacle="guarded by a dragon in a burning tower"
)

print("📜 Quest Description:\n", desc)
