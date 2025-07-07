"""
Modulo per la gestione del database nel progetto QuestMaster.
Contiene funzioni per salvare ed estrarre sessioni di generazione PDDL.
Ora supporta lore sia come JSON-string che plain text.
"""

import json
from typing import List, Dict, Union

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.schema import GenerationSession, Base

# 🔧 Connessione a SQLite
engine = create_engine("sqlite:///questmaster.db", echo=False)
Session = sessionmaker(bind=engine)


def init_db():
    """
    Inizializza il database creando tutte le tabelle se non esistono.
    """
    Base.metadata.create_all(engine)


def save_generation_session(data: Dict[str, Union[str, dict]]):
    """
    Salva una sessione di generazione PDDL nel database.

    :param data: Dizionario con chiavi: session_id, lore, domain, problem, validation,
                 refined_domain, refined_problem
    """
    session = Session()
    try:
        # Salva lore come stringa JSON se dict, altrimenti come plain text
        lore_value = data['lore']
        if isinstance(lore_value, dict):
            lore_str = json.dumps(lore_value, ensure_ascii=False)
        else:
            lore_str = str(lore_value)

        entry = GenerationSession(
            session_id=data['session_id'],
            lore=lore_str,
            domain=data['domain'],
            problem=data['problem'],
            validation=json.dumps(data['validation'], ensure_ascii=False),
            refined_domain=data.get('refined_domain'),
            refined_problem=data.get('refined_problem')
        )
        session.add(entry)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ===============================
# Retrieval with RAG
# ===============================
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def retrieve_similar_examples_from_db(input_lore: Union[dict, str], k: int = 5) -> List[Dict]:
    """
    Recupera fino a k esempi simili dal database in base alla descrizione del lore.

    :param input_lore: Lore attuale come dict (con chiave "description") o plain text string
    :param k: Numero massimo di esempi da restituire
    :return: Lista di dizionari strutturati con 'lore_description', 'domain', 'problem', 'similarity'
    """
    session = Session()
    try:
        all_sessions = session.query(GenerationSession).all()
        if not all_sessions:
            return []

        # Determina query_text
        if isinstance(input_lore, dict):
            query_text = input_lore.get('description', '')
        else:
            query_text = str(input_lore)

        corpus = []
        contents = []
        raw_refs = []

        for s in all_sessions:
            lore_raw = s.lore or ''
            # Prova a decode JSON, altrimenti plain text
            try:
                lore_obj = json.loads(lore_raw)
                lore_desc = lore_obj.get('description', lore_raw)
            except json.JSONDecodeError:
                lore_desc = lore_raw

            domain = s.domain or ''
            problem = s.problem or ''
            if '(:goal' not in problem.lower():
                continue  # scarta esempi incompleti

            corpus.append(lore_desc)
            contents.append(domain.strip() + '\n\n' + problem.strip())
            raw_refs.append((lore_desc, domain, problem))

        if not corpus:
            return []

        # Calcola TF-IDF e similarità
        vec = TfidfVectorizer().fit_transform(corpus + [query_text])
        sims = cosine_similarity(vec[-1], vec[:-1]).flatten()
        top_k = sims.argsort()[-k:][::-1]

        return [
            {
                'lore_description': raw_refs[i][0],
                'domain': raw_refs[i][1],
                'problem': raw_refs[i][2],
                'similarity': float(sims[i])
            }
            for i in top_k
        ]

    finally:
        session.close()
