# db/schema.py

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, func
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

class PipelineCheckpoint(Base):
    """
    Tabella per gestire i checkpoint della pipeline senza toccare
    la tabella interna 'checkpoints' di LangGraph
    """
    __tablename__ = "pipeline_checkpoints"
    
    id = Column(Integer, primary_key=True)
    thread_id = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), index=True) # pylint: disable=not-callable
    checkpoint = Column(Text, nullable=False) 
    user_feedback_provided = Column(Boolean, default=False, nullable=False)
    last_user_feedback = Column(Text)
    
    def __repr__(self):
        return f"<PipelineCheckpoint(thread_id='{self.thread_id}', feedback={self.user_feedback_provided})>"