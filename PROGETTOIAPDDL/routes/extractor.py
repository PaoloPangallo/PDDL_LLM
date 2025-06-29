"""Modulo Flask per l'estrazione di azioni PDDL
da frasi in linguaggio naturale tramite LangChain."""

import re
import logging
from pydantic import BaseModel, Field, ValidationError
from langchain_community.chat_models import ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from flask import Blueprint, render_template, request

extract_bp = Blueprint("extract", __name__, template_folder="templates")

MODEL = "mistral"
logger = logging.getLogger(__name__)


class PDDLAction(BaseModel):
    """Rappresentazione strutturata di un'azione PDDL, validata con Pydantic."""
    name: str = Field(..., description="Nome dell'azione")
    parameters: str = Field(..., description="Parametri dell'azione PDDL")
    precondition: str = Field(..., description="Precondizione in PDDL")
    effect: str = Field(..., description="Effetto in PDDL")

    def to_pddl(self) -> str:
        return f"""(:action {self.name}
 :parameters {self.parameters}
 :precondition {self.precondition}
 :effect {self.effect})"""


def extract_pddl_action(sentence: str) -> str:
    """Estrae un'azione PDDL valida da una frase in linguaggio naturale usando un LLM."""
    llm = ChatOllama(model=MODEL)

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content="""You are a PDDL code generator. 
Your task is to extract a single valid action definition from a natural language sentence.
Use ONLY standard PDDL syntax. Do NOT add explanations.
Return ONLY the action block.
"""),
        HumanMessage(content=f"Frase: {sentence}")
    ])

    messages = prompt.format_messages()
    response = llm.invoke(messages)
    text = response.content.strip()

    logger.debug("🧠 Risposta grezza LLM:\n%s", text)

    match = re.search(
        r"\(:action\s+(.*?)\s*:parameters\s*(\([^\)]*\))\s*:precondition\s*(\(.+?\))\s*:effect\s*(\(.+?\))\s*\)",
        text,
        re.DOTALL
    )
    if not match:
        raise ValueError("❌ Impossibile interpretare la struttura dell'azione PDDL generata.")

    try:
        parsed = PDDLAction(
            name=match.group(1).strip(),
            parameters=match.group(2).strip(),
            precondition=match.group(3).strip(),
            effect=match.group(4).strip()  # eventualmente: sanitize_effect(...)
        )
        return parsed.to_pddl()
    except ValidationError as ve:
        logger.error("❌ Errore nella validazione PDDL", exc_info=True)
        raise ValueError(f"❌ Errore nella validazione del contenuto PDDL: {ve}") from ve



@extract_bp.route('/extract', methods=['GET', 'POST'])
def extract_page():
    """Gestisce la route Flask per il form di estrazione di azioni PDDL."""
    result = None
    error = None

    if request.method == 'POST':
        sentence = request.form.get('sentence', '')
        try:
            result = extract_pddl_action(sentence)
        except Exception as e:
            logger.warning("⚠️ Errore durante l'estrazione PDDL: %s", e)
            error = str(e)

    return render_template('extract.html', result=result, error=error)
