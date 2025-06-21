# langchain_tools/quest_goal.py

"""Modulo per l'estrazione di obiettivi di quest da descrizioni testuali usando LangChain + Ollama."""
import os
from pydantic import BaseModel
from langchain_community.chat_models import ChatOllama
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

MODEL = os.getenv("OLLAMA_MODEL", "mistral")

class QuestGoal(BaseModel):
    destination: str
    required_item: str
    success_condition: str

def parse_goal_from_text(narrative: str) -> QuestGoal:
    llm = ChatOllama(model=MODEL)
    parser = PydanticOutputParser(pydantic_object=QuestGoal)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Extract the destination, required item, and success condition from the user's quest description."),
        ("human", "{input}"),
        ("system", f"Respond only using this format:\n{parser.get_format_instructions()}")
    ])

    messages = prompt.format_messages(input=narrative)
    response = llm.invoke(messages)

    return parser.parse(response.content)


