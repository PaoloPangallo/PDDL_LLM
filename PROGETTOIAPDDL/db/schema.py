# db/schema.py

from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class GenerationSession(Base):
    __tablename__ = "generation_sessions"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(64), nullable=False)
    lore = Column(Text, nullable=False)
    domain = Column(Text, nullable=True)
    problem = Column(Text, nullable=True)
    validation = Column(Text, nullable=True)
    refined_domain = Column(Text, nullable=True)
    refined_problem = Column(Text, nullable=True)
