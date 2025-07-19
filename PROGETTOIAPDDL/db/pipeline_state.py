import json
import logging
from typing import Dict, Any, Optional, Callable
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session
from db.schema import Base, PipelineCheckpoint

logger = logging.getLogger(__name__)

# Configurazione database
DATABASE_URL = "sqlite:///pipeline_state.db"
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Crea tabelle se non esistono
Base.metadata.create_all(bind=engine)

def get_db_session() -> Session:
    """Restituisce una sessione database"""
    return SessionLocal()

def get_last_app_checkpoint(thread_id: str) -> Optional[Dict[str, Any]]:
    """
    Ottiene l'ultimo checkpoint salvato per il thread specificato
    
    Args:
        thread_id: ID del thread
        
    Returns:
        Dict contenente i dati del checkpoint o None se non trovato
    """
    try:
        with get_db_session() as session:
            checkpoint = session.query(PipelineCheckpoint).filter(
                PipelineCheckpoint.thread_id == thread_id
            ).order_by(desc(PipelineCheckpoint.created_at)).first()
            
            if checkpoint:
                data = json.loads(str(checkpoint.checkpoint))
                data.update({
                    "_user_feedback_provided": checkpoint.user_feedback_provided,
                    "_last_user_feedback": checkpoint.last_user_feedback,
                    "_checkpoint_id": checkpoint.id,
                    "_created_at": checkpoint.created_at.isoformat() if checkpoint.created_at is not None else None
                })
                
                logger.info("📥 Caricato checkpoint per thread %s (ID: %d)", thread_id, checkpoint.id)
                return data
            else:
                logger.info("📭 Nessun checkpoint trovato per thread: %s", thread_id)
                return None
                
    except Exception as e:
        logger.error("❌ Errore caricamento checkpoint per thread %s: %s", thread_id, e)
        return None

def save_app_checkpoint(
    thread_id: str, 
    data_dict: Dict[str, Any], 
    feedback: bool = False, 
    feedback_text: Optional[str] = None
) -> bool:
    """
    Salva un nuovo checkpoint per il thread specificato
    
    Args:
        thread_id: ID del thread
        data_dict: Dati da salvare (domain, problem, lore, flags, etc.)
        feedback: True se questo salvataggio include feedback utente
        feedback_text: Testo del feedback dell'utente (opzionale)
        
    Returns:
        True se salvato con successo, False altrimenti
    """
    try:
        # Rimuovi metadati interni prima del salvataggio
        clean_data = {k: v for k, v in data_dict.items() 
                      if not k.startswith('_') or k in ['_waiting_for_edit', '_resume_after_feedback']}
        
        checkpoint_json = json.dumps(clean_data, ensure_ascii=False, default=str)
        
        with get_db_session() as session:
            new_checkpoint = PipelineCheckpoint(
                thread_id=thread_id,
                checkpoint=checkpoint_json,
                user_feedback_provided=feedback,
                last_user_feedback=feedback_text
            )
            
            session.add(new_checkpoint)
            session.commit()
            
            logger.info("✅ Salvato checkpoint per thread %s (feedback: %s, ID: %d)", 
                       thread_id, feedback, new_checkpoint.id)
            return True
            
    except Exception as e:
        logger.error("❌ Errore salvataggio checkpoint per thread %s: %s", thread_id, e)
        return False

def mark_feedback(
    thread_id: str, 
    feedback_text: str, 
    mutator: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
) -> bool:
    """
    Marca il feedback dell'utente e opzionalmente modifica i dati del checkpoint
    
    Args:
        thread_id: ID del thread
        feedback_text: Testo del feedback fornito dall'utente
        mutator: Funzione opzionale per modificare i dati prima del salvataggio
                 (riceve il dict corrente e restituisce il dict modificato)
        
    Returns:
        True se aggiornato con successo, False altrimenti
    """
    try:
        # Carica l'ultimo checkpoint
        current_data = get_last_app_checkpoint(thread_id)
        if not current_data:
            logger.warning("⚠️ Nessun checkpoint esistente per applicare feedback: %s", thread_id)
            return False
        
        # Applica il mutator se fornito
        if mutator:
            try:
                current_data = mutator(current_data)
                logger.info("🔧 Mutator applicato ai dati del checkpoint per thread: %s", thread_id)
            except Exception as e:
                logger.error("❌ Errore nell'applicazione del mutator: %s", e)
                return False
        
        # Aggiungi flag di feedback
        current_data["_user_feedback_provided"] = True
        current_data["_waiting_for_edit"] = False
        current_data["_resume_after_feedback"] = True
        
        # Salva nuovo checkpoint con feedback
        success = save_app_checkpoint(
            thread_id=thread_id,
            data_dict=current_data,
            feedback=True,
            feedback_text=feedback_text
        )
        
        if success:
            logger.info("✅ Feedback marcato per thread %s: %s", thread_id, feedback_text[:100])
        
        return success
        
    except Exception as e:
        logger.error("❌ Errore marcatura feedback per thread %s: %s", thread_id, e)
        return False

def is_pipeline_waiting_for_edit(thread_id: str) -> bool:
    """
    Controlla se la pipeline è in attesa di editing dall'utente
    
    Args:
        thread_id: ID del thread
        
    Returns:
        True se in attesa di editing, False altrimenti
    """
    data = get_last_app_checkpoint(thread_id)
    if not data:
        return False
    
    # Controlla flag di attesa editing
    waiting = data.get("_waiting_for_edit", False)
    has_feedback = data.get("_user_feedback_provided", False)
    
    # In attesa solo se flag è True e feedback non ancora fornito
    result = waiting and not has_feedback
    
    if result:
        logger.info("✋ Pipeline in attesa di editing per thread: %s", thread_id)
    
    return result

def reset_pipeline_state(thread_id: str) -> bool:
    """
    Reset completo dello stato della pipeline (elimina tutti i checkpoint)
    
    Args:
        thread_id: ID del thread
        
    Returns:
        True se resettato con successo, False altrimenti
    """
    try:
        with get_db_session() as session:
            deleted_count = session.query(PipelineCheckpoint).filter(
                PipelineCheckpoint.thread_id == thread_id
            ).delete()
            
            session.commit()
            
            logger.info("🧹 Reset pipeline state per thread %s (%d checkpoint eliminati)", 
                       thread_id, deleted_count)
            return True
            
    except Exception as e:
        logger.error("❌ Errore reset pipeline state per thread %s: %s", thread_id, e)
        return False

def get_pipeline_stats(thread_id: str) -> Dict[str, Any]:
    """
    Statistiche sui checkpoint di una pipeline
    
    Args:
        thread_id: ID del thread
        
    Returns:
        Dict con statistiche (count, feedback_count, last_update, etc.)
    """
    try:
        with get_db_session() as session:
            total_count = session.query(PipelineCheckpoint).filter(
                PipelineCheckpoint.thread_id == thread_id
            ).count()
            
            feedback_count = session.query(PipelineCheckpoint).filter(
                PipelineCheckpoint.thread_id == thread_id,
                PipelineCheckpoint.user_feedback_provided == True
            ).count()
            
            last_checkpoint = session.query(PipelineCheckpoint).filter(
                PipelineCheckpoint.thread_id == thread_id
            ).order_by(desc(PipelineCheckpoint.created_at)).first()
            
            return {
                "thread_id": thread_id,
                "total_checkpoints": total_count,
                "feedback_checkpoints": feedback_count,
                "last_update": last_checkpoint.created_at.isoformat() if last_checkpoint and last_checkpoint.created_at is not None else None,
                "has_data": total_count > 0,
                "waiting_for_edit": is_pipeline_waiting_for_edit(thread_id)
            }
            
    except Exception as e:
        logger.error("❌ Errore recupero statistiche per thread %s: %s", thread_id, e)
        return {
            "thread_id": thread_id,
            "total_checkpoints": 0,
            "feedback_checkpoints": 0,
            "last_update": None,
            "has_data": False,
            "waiting_for_edit": False,
            "error": str(e)
        }