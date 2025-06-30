# db/db.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.schema import GenerationSession, Base

# 🔧 Connessione a SQLite
engine = create_engine("sqlite:///questmaster.db", echo=False)
Session = sessionmaker(bind=engine)

# ✅ Crea le tabelle se non esistono
Base.metadata.create_all(engine)

def save_generation_session(data: dict):
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
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
        
        
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json

def retrieve_similar_examples_from_db(input_lore: dict, k: int = 1) -> list[str]:
    session = Session()
    try:
        all_sessions = session.query(GenerationSession).all()
        if not all_sessions:
            return []

        # Testo del nuovo lore
        query_text = input_lore.get("description", "")

        # Corpus: le lore description salvate
        corpus = []
        contents = []
        for s in all_sessions:
            try:
                old_lore = json.loads(s.lore)
                corpus.append(old_lore.get("description", ""))
                domain = s.domain or ""
                problem = s.problem or ""
                contents.append(domain.strip() + "\n\n" + problem.strip())
            except Exception as e:
                continue

        vec = TfidfVectorizer().fit_transform(corpus + [query_text])
        sims = cosine_similarity(vec[-1], vec[:-1]).flatten()

        top_k = sims.argsort()[-k:][::-1]
        return [contents[i] for i in top_k]

    finally:
        session.close()
        
def init_db():
    Base.metadata.create_all(engine)

