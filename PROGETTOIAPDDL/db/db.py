"""
Modulo per la gestione del database nel progetto QuestMaster.
Contiene funzioni per salvare ed estrarre sessioni di generazione PDDL.
"""

import json
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from db.schema import GenerationSession, Base

# 🔧 Connessione a SQLite
engine = create_engine("sqlite:///questmaster.db", echo=False)
Session = sessionmaker(bind=engine)


def init_db():
    """
    Inizializza il database creando tutte le tabelle se non esistono.
    """
    Base.metadata.create_all(engine)


def save_generation_session(data: dict):
    """
    Salva una sessione di generazione PDDL nel database.

    :param data: Dizionario con chiavi: session_id, lore, domain, problem, validation,
                 refined_domain, refined_problem
    """
    session = Session()
    try:
        entry = GenerationSession(
            session_id=data["session_id"],
            lore=data["lore"],
            domain=data["domain"],
            problem=data["problem"],
            validation=data["validation"],
            refined_domain=data.get("refined_domain"),
            refined_problem=data.get("refined_problem")
        )
        session.add(entry)
        session.commit()
    except Exception:  # È meglio evitare di catturare `Exception` generico; specificare in futuro.
        session.rollback()
        raise
    finally:
        session.close()


def retrieve_similar_examples_from_db(input_lore: dict, k: int = 1) -> List[str]:
    """
    Recupera fino a k esempi simili dal database in base alla descrizione del lore.

    :param input_lore: Dizionario contenente la chiave "description"
    :param k: Numero di esempi da restituire
    :return: Lista di stringhe con contenuti PDDL simili
    """
    session = Session()
    try:
        all_sessions = session.query(GenerationSession).all()
        if not all_sessions:
            return []

        query_text = input_lore.get("description", "")
        corpus = []
        contents = []

        for s in all_sessions:
            try:
                old_lore = json.loads(s.lore)
                corpus.append(old_lore.get("description", ""))
                domain = s.domain or ""
                problem = s.problem or ""
                contents.append(domain.strip() + "\n\n" + problem.strip())
            except json.JSONDecodeError:
                continue  # Ignora entry non valide nel lore

        vec = TfidfVectorizer().fit_transform(corpus + [query_text])
        sims = cosine_similarity(vec[-1], vec[:-1]).flatten()

        top_k = sims.argsort()[-k:][::-1]
        return [contents[i] for i in top_k]

    finally:
        session.close()


