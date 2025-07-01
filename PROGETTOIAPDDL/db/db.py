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


from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json

def retrieve_similar_examples_from_db(input_lore: dict, k: int = 5) -> List[Dict]:
    """
    Recupera fino a k esempi strutturati simili dal database in base alla descrizione del lore.

    :param input_lore: Lore attuale come dict (richiede chiave "description")
    :param k: Numero massimo di esempi da restituire
    :return: Lista di dizionari strutturati con 'lore_description', 'domain', 'problem', 'similarity'
    """
    session = Session()
    try:
        all_sessions = session.query(GenerationSession).all()
        if not all_sessions:
            return []

        query_text = input_lore.get("description", "")
        corpus = []
        contents = []
        raw_refs = []

        for s in all_sessions:
            try:
                old_lore = json.loads(s.lore)
                lore_desc = old_lore.get("description", "")
                domain = s.domain or ""
                problem = s.problem or ""
                
                if "(:goal" not in problem:
                    continue  # scarta esempi incompleti

                corpus.append(lore_desc)
                contents.append(domain.strip() + "\n\n" + problem.strip())
                raw_refs.append((lore_desc, domain, problem))
            except json.JSONDecodeError:
                continue

        if not corpus:
            return []

        vec = TfidfVectorizer().fit_transform(corpus + [query_text])
        sims = cosine_similarity(vec[-1], vec[:-1]).flatten()
        top_k = sims.argsort()[-k:][::-1]

        return [
            {
                "lore_description": raw_refs[i][0],
                "domain": raw_refs[i][1],
                "problem": raw_refs[i][2],
                "similarity": float(sims[i])
            }
            for i in top_k
        ]

    finally:
        session.close()



