"""Modulo per la generazione automatica di descrizioni di quest usando LangChain + Ollama."""

import os
from langchain_community.chat_models.ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

MODEL = os.getenv("OLLAMA_MODEL", "mistral")  # oppure "tinyllama"


def generate_quest_description(goal: str, obstacle: str) -> str:
    """
    Genera una breve descrizione narrativa di una quest a partire da obiettivo e ostacolo.

    Usa LangChain + Ollama per creare un'introduzione coerente e accattivante.
    """
    llm = ChatOllama(model=MODEL)

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=(
            "You are a fantasy narrative designer. Your job is to turn a simple quest goal "
            "and obstacle into a compelling one-paragraph quest introduction."
        )),
        HumanMessage(content="Goal: {goal}\nObstacle: {obstacle}")
    ])

    messages = prompt.format_messages(goal=goal, obstacle=obstacle)
    response = llm.invoke(messages)

    return response.content.strip()

