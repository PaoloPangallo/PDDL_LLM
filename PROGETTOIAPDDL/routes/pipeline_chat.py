from __future__ import annotations
import os
import json
import logging
import shutil
import sqlite3
from pathlib import Path
from typing import cast, Any, Dict, Optional, Union, Generator
from flask import Blueprint, request, jsonify, url_for, Response, stream_with_context
from flask.typing import ResponseReturnValue
from langchain_core.messages import HumanMessage, BaseMessage
from graphs.pddl_pipeline_graph import get_pipeline_with_memory, PipelineState
from langgraph.types import Command, Interrupt
from langchain_core.runnables.config import RunnableConfig
from core.utils import save_text_file, save_pipeline_state
from db.schema import Base, GenerationSession, PipelineCheckpoint
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime

# Cache globali per gestione unificata dello stato
_graph_cache: Dict[str, Any] = {}
_pipeline_states: Dict[str, Dict[str, Any]] = {}

pipeline_chat_bp = Blueprint("pipeline_chat", __name__)
logger = logging.getLogger(__name__)

# Setup logging se necessario
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

# Setup database
def get_db_session(thread_id: str) -> Session:
    """Crea una sessione database per il thread specifico"""
    db_path = f"memory/{thread_id}.db"
    os.makedirs("memory", exist_ok=True)
    
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()

def serialize_value(val: Any) -> Any:
    """Serializza valori per JSON, gestendo BaseMessage e strutture complesse"""
    if isinstance(val, BaseMessage):
        return {"type": val.type, "content": val.content}
    elif isinstance(val, list):
        return [serialize_value(v) for v in val]
    elif isinstance(val, dict):
        return {k: serialize_value(v) for k, v in val.items()}
    return val

def copy_generated_files(result: Dict[str, Any], thread_id: str) -> Dict[str, str]:
    """Copia i file generati nella directory static e restituisce gli URL"""
    gen_dir = os.path.join("static", "generated", thread_id)
    os.makedirs(gen_dir, exist_ok=True)
    
    files_map = {
        "raw_response": "raw_response.txt",
        "domain": "domain.pddl",
        "problem": "problem.pddl",
        "refined_domain": "domain_refined.pddl",
        "refined_problem": "problem_refined.pddl",
    }
    
    urls: Dict[str, str] = {}
    tmp_dir = result.get("tmp_dir")
    if tmp_dir:
        for key, fname in files_map.items():
            src = os.path.join(tmp_dir, fname)
            if os.path.exists(src):
                dst = os.path.join(gen_dir, fname)
                shutil.copy(src, dst)
                urls[f"{key}_url"] = url_for(
                    "static", filename=f"generated/{thread_id}/{fname}"
                )
    return urls

def load_lore(lore_param: Optional[str], custom_story: Optional[str] = None) -> Dict[str, Any]:
    """Carica la configurazione lore"""
    if lore_param == "_free_":
        lore_text = (custom_story or "").strip()
        return {"id": "custom", "text": lore_text, "preset": False}
    
    if not lore_param:
        raise ValueError("Parametro 'lore' mancante")
    
    lore_path = Path("lore") / lore_param
    if not lore_path.exists():
        raise FileNotFoundError(f"Lore '{lore_param}' non trovata")
    
    lore_dict = json.loads(lore_path.read_text("utf-8"))
    lore_dict.setdefault("id", lore_path.stem)
    lore_dict["preset"] = True
    return lore_dict

def get_pipeline_state(thread_id: str) -> Optional[Dict[str, Any]]:
    """Ottiene lo stato corrente della pipeline dal nuovo schema"""
    try:
        db_session = get_db_session(thread_id)
        try:
            # Prima controlla la tabella PipelineCheckpoint
            checkpoint = db_session.query(PipelineCheckpoint)\
                .filter_by(thread_id=thread_id)\
                .order_by(desc(PipelineCheckpoint.created_at))\
                .first()
            
            if checkpoint:
                # CORREZIONE: Accedi ai valori delle colonne, non alle colonne stesse
                checkpoint_data = json.loads(str(checkpoint.checkpoint))
                state = checkpoint_data.get("channel_values", {})
                
                # Aggiungi metadati dal checkpoint
                state["_user_feedback_provided"] = checkpoint.user_feedback_provided
                state["_last_user_feedback"] = checkpoint.last_user_feedback
                state["_waiting_for_edit"] = checkpoint.user_feedback_provided is None
                
                return state
            
            # Fallback: controlla la tabella LangGraph se esiste
            db_path = f"memory/{thread_id}.sqlite"
            if os.path.exists(db_path):
                with sqlite3.connect(db_path, check_same_thread=True) as conn:
                    cursor = conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='checkpoints'"
                    )
                    if cursor.fetchone():
                        cursor = conn.execute(
                            "SELECT checkpoint FROM checkpoints ORDER BY thread_ts DESC LIMIT 1"
                        )
                        row = cursor.fetchone()
                        if row:
                            checkpoint_data = json.loads(row[0])
                            return checkpoint_data.get("channel_values", {})
                            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error("Errore lettura stato pipeline: %s", e)
    
    return None

def save_pipeline_checkpoint(thread_id: str, state_data: Dict[str, Any], 
                           user_feedback_provided: bool = False, 
                           last_user_feedback: Optional[str] = None) -> None:
    """Salva un checkpoint della pipeline nel nuovo schema"""
    try:
        db_session = get_db_session(thread_id)
        try:
            checkpoint = PipelineCheckpoint(
                thread_id=thread_id,
                checkpoint=json.dumps({"channel_values": state_data}, ensure_ascii=False),
                user_feedback_provided=user_feedback_provided,
                last_user_feedback=last_user_feedback
            )
            
            db_session.add(checkpoint)
            db_session.commit()
            
            logger.info("✅ Checkpoint salvato per thread: %s", thread_id)
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error("❌ Errore salvataggio checkpoint: %s", e)

def update_generation_session(thread_id: str, **kwargs) -> None:
    """Aggiorna o crea una sessione di generazione"""
    try:
        db_session = get_db_session(thread_id)
        try:
            session = db_session.query(GenerationSession)\
                .filter_by(session_id=thread_id)\
                .first()
            
            if not session:
                session = GenerationSession(session_id=thread_id)
                db_session.add(session)
            
            # Aggiorna campi forniti
            for key, value in kwargs.items():
                if hasattr(session, key):
                    if isinstance(value, (dict, list)):
                        setattr(session, key, json.dumps(value, ensure_ascii=False))
                    else:
                        setattr(session, key, value)
            
            db_session.commit()
            logger.info("✅ GenerationSession aggiornata per thread: %s", thread_id)
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error("❌ Errore aggiornamento GenerationSession: %s", e)

def is_pipeline_waiting_for_edit(thread_id: str) -> bool:
    """Controlla se la pipeline è in attesa di editing dall'utente"""
    try:
        db_session = get_db_session(thread_id)
        try:
            checkpoint = db_session.query(PipelineCheckpoint)\
                .filter_by(thread_id=thread_id)\
                .order_by(desc(PipelineCheckpoint.created_at))\
                .first()
            
            if checkpoint:
                # CORREZIONE: Controlla il valore booleano della colonna, non la colonna stessa
                if not checkpoint.user_feedback_provided is None:
                    checkpoint_data = json.loads(str(checkpoint.checkpoint))
                    state = checkpoint_data.get("channel_values", {})
                    
                    # Controlla se c'è una interruzione con domain/problem
                    if "__interrupt__" in state:
                        interrupt_item = state["__interrupt__"]
                        payload = None
                        
                        if isinstance(interrupt_item, dict) and "value" in interrupt_item:
                            payload = interrupt_item["value"]
                        elif isinstance(interrupt_item, (list, tuple)) and len(interrupt_item) > 0:
                            first_item = interrupt_item[0]
                            if isinstance(first_item, dict) and "value" in first_item:
                                payload = first_item["value"]
                        
                        if payload and isinstance(payload, dict):
                            return "domain" in payload and "problem" in payload
                
                return False
                
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error("Errore controllo stato editing: %s", e)
    
    return False

def get_or_create_pipeline_state(thread_id: str, lore_dict: Dict[str, Any], reset: bool = False) -> Dict[str, Any]:
    """Ottiene pipeline esistente o ne crea una nuova SOLO se necessario"""
    
    # Se reset esplicito, pulisci tutto
    if reset:
        logger.info("🧹 Reset esplicito richiesto per thread: %s", thread_id)
        
        # Pulisci database personalizzato
        db_path = f"memory/{thread_id}.db"
        if os.path.exists(db_path):
            os.remove(db_path)
        
        # Pulisci database LangGraph se esiste
        mem_db = f"memory/{thread_id}.sqlite"
        if os.path.exists(mem_db):
            os.remove(mem_db)
            
        _graph_cache.pop(thread_id, None)
        _pipeline_states.pop(thread_id, None)
        
        return {
            "thread_id": thread_id,
            "lore": lore_dict,
            "messages": [],
            "config": lore_dict,
            "is_new": True
        }
    
    # Controlla se esiste pipeline attiva
    existing_state = get_pipeline_state(thread_id)
    
    if existing_state:
        logger.info("♻️  Pipeline esistente trovata per thread: %s", thread_id)
        return {
            "thread_id": thread_id,
            "lore": existing_state.get("lore", lore_dict),
            "tmp_dir": existing_state.get("tmp_dir"),
            "domain": existing_state.get("domain"),
            "problem": existing_state.get("problem"),
            "messages": [],
            "is_new": False,
            "existing": True
        }
    else:
        logger.info("🆕 Nuova pipeline per thread: %s", thread_id)
        return {
            "thread_id": thread_id,
            "lore": lore_dict,
            "messages": [],
            "config": lore_dict,
            "is_new": True
        }


def update_pipeline_with_feedback(thread_id: str, domain: str, problem: str) -> None:
    """Aggiorna il database con il feedback dell'utente - Versione SQLAlchemy CORRETTA"""
    try:
        db_session = get_db_session(thread_id)
        try:
            # Ottieni l'ultimo checkpoint
            checkpoint = db_session.query(PipelineCheckpoint)\
                .filter_by(thread_id=thread_id)\
                .order_by(desc(PipelineCheckpoint.created_at))\
                .first()
            
            if not checkpoint:
                logger.warning("Nessun checkpoint trovato per thread: %s", thread_id)
                
                # Crea un nuovo checkpoint con il feedback
                feedback_state = {
                    "domain": domain,
                    "problem": problem,
                    "thread_id": thread_id,
                    "_user_feedback_provided": True,
                    "_waiting_for_edit": False,
                    "messages": [{
                        "type": "human",
                        "content": f"User feedback - Domain: {domain}\nProblem: {problem}"
                    }]
                }
                
                new_checkpoint = PipelineCheckpoint(
                    thread_id=thread_id,
                    checkpoint=json.dumps({"channel_values": feedback_state}, ensure_ascii=False),
                    user_feedback_provided=True,
                    last_user_feedback=f"Domain: {domain}\nProblem: {problem}"
                )
                
                db_session.add(new_checkpoint)
                db_session.commit()
                
                logger.info("✅ Nuovo checkpoint creato con feedback per thread: %s", thread_id)
                return
                
            # Aggiorna checkpoint esistente - CORREZIONE QUI
            checkpoint_data = json.loads(str(checkpoint.checkpoint))
            channel_values = checkpoint_data.get("channel_values", {})
            
            # Rimuovi l'interruzione e aggiungi il feedback
            if "__interrupt__" in channel_values:
                del channel_values["__interrupt__"]
            
            # Aggiorna domain e problem nel checkpoint
            channel_values["domain"] = domain
            channel_values["problem"] = problem
            channel_values["_user_feedback_provided"] = True
            channel_values["_waiting_for_edit"] = False
            
            # Crea messaggio di feedback
            feedback_message = {
                "type": "human",
                "content": f"User feedback - Domain: {domain}\nProblem: {problem}"
            }
            
            if "messages" not in channel_values:
                channel_values["messages"] = []
            channel_values["messages"].append(feedback_message)
            
            # CORREZIONE: Usa il metodo update() invece di assegnazione diretta
            db_session.query(PipelineCheckpoint)\
                .filter_by(thread_id=thread_id, id=checkpoint.id)\
                .update({
                    "checkpoint": json.dumps({"channel_values": channel_values}, ensure_ascii=False),
                    "user_feedback_provided": True,
                    "last_user_feedback": f"Domain: {domain}\nProblem: {problem}",
                    "updated_at": datetime.utcnow()  # Aggiungi timestamp se necessario
                })
            
            db_session.commit()
            
            # Aggiorna anche la GenerationSession
            update_generation_session(
                thread_id, 
                domain=domain, 
                problem=problem
            )
            
            logger.info("✅ Checkpoint aggiornato con feedback utente per thread: %s", thread_id)
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error("❌ Errore aggiornamento checkpoint: %s", e)

@pipeline_chat_bp.route("/message", methods=["POST"])
def handle_pipeline_chat() -> ResponseReturnValue:
    """Endpoint per gestire messaggi della pipeline (POST)"""
    try:
        data: Dict[str, Any] = request.get_json(force=True) or {}
        thread_id = data.get("thread_id", "session-1")
        reset = bool(data.get("reset", False))

        config: RunnableConfig = {
            "configurable": {"thread_id": thread_id}
        }

        # Ottieni il grafo
        graph = get_pipeline_with_memory(thread_id, reset=reset)

        # ═══════ A) RIPRESA DOPO EDIT UTENTE ═══════
        if "domain" in data and "problem" in data:
            logger.info("✍️ Resume con domain/problem modificati")
            
            # CHIAVE: Aggiorna il checkpoint prima di riprendere
            update_pipeline_with_feedback(thread_id, data["domain"], data["problem"])
            
            # Crea stato per resume senza resettare
            resume_state: PipelineState = cast(PipelineState, {
                "messages": [],
                "thread_id": thread_id,
                "_resume_after_feedback": True
            })
            
            result = graph.invoke(resume_state, config=config)

        # ═══════ B) GESTIONE MESSAGGI TESTUALI ═══════
        elif "message" in data:
            logger.info("💬 Messaggio testuale ricevuto")
            
            user_message = HumanMessage(content=data["message"])
            message_state: PipelineState = cast(PipelineState, {
                "messages": [user_message],
                "thread_id": thread_id
            })
            
            result = graph.invoke(message_state, config=config)

        # ═══════ C) AVVIO INIZIALE ═══════
        else:
            logger.info("⚡ Avvio pipeline completa")
            
            # Carica lore solo per nuove pipeline
            lore_dict = load_lore(data.get("lore"), data.get("custom_story"))
            
            # Usa gestione unificata dello stato
            pipeline_state = get_or_create_pipeline_state(thread_id, lore_dict, reset)
            
            initial_state: PipelineState = cast(PipelineState, pipeline_state)
            result = graph.invoke(initial_state, config=config)
            
            # Salva risultato nel nuovo schema
            if result:
                update_generation_session(
                    thread_id,
                    lore=lore_dict,
                    domain=result.get("domain"),
                    problem=result.get("problem"),
                    validation=result.get("validation"),
                    refined_domain=result.get("refined_domain"),
                    refined_problem=result.get("refined_problem")
                )

        # Estrai ultimo messaggio AI
        response_text: Optional[str] = None
        for msg in result.get("messages", []):
            if isinstance(msg, dict) and msg.get("type") == "ai":
                response_text = str(msg["content"])
                break

        # Copia file generati
        urls = copy_generated_files(result, thread_id)

        return jsonify({
            "response": response_text or "⚠️ Nessuna risposta generata.",
            "prompt": result.get("prompt"),
            "validation": result.get("validation"),
            "refined_domain": result.get("refined_domain"),
            "refined_problem": result.get("refined_problem"),
            **urls,
        })

    except (ValueError, FileNotFoundError) as e:
        logger.error("❌ Errore validazione: %s", str(e))
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("❌ Errore nella pipeline")
        return jsonify({"error": str(e)}), 500

@pipeline_chat_bp.route("/stream", methods=["GET"])
def stream_pipeline() -> ResponseReturnValue:
    """Endpoint per streaming della pipeline (GET)"""
    try:
        # Parametri
        thread_id = request.args.get("thread_id", "session-1")
        lore_param = request.args.get("lore")
        custom_story = request.args.get("custom_story")
        reset = request.args.get("reset", "false").lower() == "true"

        config: RunnableConfig = {
            "configurable": {"thread_id": thread_id}
        }

        logger.info("🎬 Stream request - thread_id: %s, reset: %s", thread_id, reset)

        # Controlla se pipeline è in attesa di editing
        waiting_for_edit = is_pipeline_waiting_for_edit(thread_id)
        
        if waiting_for_edit and not reset:
            logger.info("✋ Pipeline in attesa di editing, invio stato per continuare")
            
            def edit_resume_stream() -> Generator[str, None, None]:
                try:
                    # Ottieni lo stato corrente
                    current_state = get_pipeline_state(thread_id)
                    if current_state and current_state.get("_user_feedback_provided"):
                        # Feedback fornito, riprendi pipeline
                        graph = get_pipeline_with_memory(thread_id, reset=False)
                        
                        resume_state: PipelineState = cast(PipelineState, {
                            "messages": [],
                            "thread_id": thread_id,
                            "_resume_after_feedback": True
                        })
                        
                        for chunk in graph.stream(resume_state, config=config):
                            yield from process_stream_chunk(chunk, thread_id)
                    else:
                        if current_state is None:
                            raise ValueError("current_state mancante")
                        domain = current_state.get("domain", "")
                        problem = current_state.get("problem", "")
                        payload = {"domain": domain, "problem": problem}
                        
                        yield f"event: ChatFeedback\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                        yield "event: PauseForFeedback\ndata: {{}}\n\n"
                        yield "event: stream_paused\ndata: {{}}\n\n"
                    
                    yield "event: done\ndata: {{}}\n\n"
                    
                except Exception as e:
                    logger.exception("Errore durante edit resume stream")
                    yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"

            return Response(
                stream_with_context(edit_resume_stream()), 
                mimetype="text/event-stream",
                headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive'}
            )

        # Reset se esplicitamente richiesto
        if reset:
            # Pulisci entrambi i database
            db_path = f"memory/{thread_id}.db"
            if os.path.exists(db_path):
                os.remove(db_path)
                
            mem_db = f"memory/{thread_id}.sqlite"
            if os.path.exists(mem_db):
                os.remove(mem_db)
                logger.info("🧹 Database reset per stream: %s", mem_db)
                
            _graph_cache.pop(thread_id, None)
            _pipeline_states.pop(thread_id, None)

        # Carica lore per nuove pipeline
        lore_dict = load_lore(lore_param, custom_story)
        
        # Usa gestione unificata dello stato
        pipeline_state_data = get_or_create_pipeline_state(thread_id, lore_dict, reset)
        
        # Ottieni grafo
        graph = get_pipeline_with_memory(thread_id, reset=reset)
        
        def unified_event_stream() -> Generator[str, None, None]:
            """Generator unificato per Server-Sent Events"""
            try:
                initial_state: PipelineState = cast(PipelineState, pipeline_state_data)
                
                logger.info("🚀 Avvio stream con stato: %s", 
                           "nuovo" if pipeline_state_data.get("is_new") else "esistente")
                
                for chunk in graph.stream(initial_state, config=config):
                    yield from process_stream_chunk(chunk, thread_id)
                
                yield "event: done\ndata: {{}}\n\n"
                
            except StopIteration:
                yield "event: done\ndata: {{}}\n\n"
            except Exception as e:
                logger.exception("Errore in unified_event_stream")
                yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"
                yield "event: done\ndata: {{}}\n\n"

        return Response(
            stream_with_context(unified_event_stream()), 
            mimetype="text/event-stream",
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            }
        )

    except (ValueError, FileNotFoundError) as e:
        logger.error("❌ Errore validazione stream: %s", str(e))
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("❌ Errore critico nello stream")
        return jsonify({"error": str(e)}), 500

def process_stream_chunk(chunk: Dict[str, Any], thread_id: str) -> Generator[str, None, None]:
    """Processa un singolo chunk dello stream in modo unificato"""
    try:
        # Salva gli stati importanti nel database
        chunk_data = {}
        
        for key in ["domain", "problem", "validation", "refined_domain", "refined_problem"]:
            if key in chunk:
                chunk_data[key] = chunk[key]
        
        if chunk_data:
            # Aggiorna lo stato della pipeline
            save_pipeline_checkpoint(thread_id, chunk_data)
            
            # Aggiorna la sessione di generazione
            update_generation_session(thread_id, **chunk_data)
        
        # Gestisci interruzioni in modo selettivo
        if "__interrupt__" in chunk:
            interrupt_item = chunk["__interrupt__"]
            interrupt_obj: Optional[Interrupt] = None
            
            # Estrai oggetto Interrupt
            if isinstance(interrupt_item, Interrupt):
                interrupt_obj = interrupt_item
            elif isinstance(interrupt_item, list) and interrupt_item:
                candidate = interrupt_item[0]
                if isinstance(candidate, Interrupt):
                    interrupt_obj = candidate
            elif isinstance(interrupt_item, tuple) and interrupt_item:
                if isinstance(interrupt_item[0], Interrupt):
                    interrupt_obj = interrupt_item[0]
            
            if interrupt_obj:
                payload = interrupt_obj.value
                
                # Solo interruzioni con domain/problem vanno in editing
                if isinstance(payload, dict) and "domain" in payload and "problem" in payload:
                    logger.info("🛑 Interruzione stream per editing: %s", payload)
                    
                    # Salva lo stato dell'interruzione
                    interrupt_state = {
                        "domain": payload.get("domain", ""),
                        "problem": payload.get("problem", ""),
                        "_waiting_for_edit": True,
                        "__interrupt__": payload
                    }
                    
                    save_pipeline_checkpoint(thread_id, interrupt_state, user_feedback_provided=False)
                    
                    yield f"event: ChatFeedback\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    yield "event: PauseForFeedback\ndata: {{}}\n\n"
                    yield "event: stream_paused\ndata: {{}}\n\n"
                    return
                else:
                    # Altre interruzioni sono normali eventi di stato
                    logger.info("📊 Interruzione di stato normale: %s", payload)
                    yield f"event: status_interrupt\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            else:
                logger.error("Impossibile estrarre oggetto Interrupt da: %s", interrupt_item)
        
        # Emetti altri eventi normalmente
        for key, val in chunk.items():
            if key != "__interrupt__":
                yield f"event: {key}\ndata: {json.dumps(serialize_value(val), ensure_ascii=False)}\n\n"
                
    except Exception as e:
        logger.exception("Errore processamento chunk: %s", chunk)
        yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"

@pipeline_chat_bp.route("/resume", methods=["POST"])
def resume_pipeline() -> ResponseReturnValue:
    """Endpoint per il resume della pipeline dopo editing"""
    try:
        data: Dict[str, Any] = request.get_json(force=True) or {}
        thread_id = data.get("thread_id", "session-1")
        domain = data.get("domain", "")
        problem = data.get("problem", "")

        if not domain or not problem:
            return jsonify({"error": "Domain e Problem sono richiesti per il resume"}), 400

        logger.info("🔄 Resume request - thread_id: %s", thread_id)

        # CHIAVE: Aggiorna il checkpoint con il feedback
        update_pipeline_with_feedback(thread_id, domain, problem)

        # Restituisci solo conferma - il resume avverrà tramite stream
        return jsonify({
            "response": "✅ Feedback ricevuto, pipeline riprenderà dal checkpoint.",
            "status": "feedback_received"
        })

    except Exception as e:
        logger.exception("❌ Errore nel resume")
        return jsonify({"error": str(e)}), 500

@pipeline_chat_bp.route("/status/<thread_id>", methods=["GET"])
def get_pipeline_status(thread_id: str) -> ResponseReturnValue:
    """Endpoint per controllare lo stato della pipeline"""
    try:
        state = get_pipeline_state(thread_id)
        waiting_for_edit = is_pipeline_waiting_for_edit(thread_id)
        
        # Ottieni anche informazioni dalla GenerationSession
        session_info = {}
        try:
            db_session = get_db_session(thread_id)
            try:
                session = db_session.query(GenerationSession)\
                    .filter_by(session_id=thread_id)\
                    .first()
                
                if session:
                    session_info = {
                        "has_domain": bool(session.domain),
                        "has_problem": bool(session.problem),
                        "has_validation": bool(session.validation),
                        "has_refinements": bool(session.refined_domain and session.refined_problem),
                        "created_at": session.created_at.isoformat() if session.created_at else None,
                        "updated_at": session.updated_at.isoformat() if session.updated_at else None
                    }
            finally:
                db_session.close()
        except Exception as e:
            logger.error("Errore lettura GenerationSession: %s", e)
            session_info = {"error": str(e)}
        
        # Costruisci risposta completa
        status_response = {
            "thread_id": thread_id,
            "has_state": bool(state),
            "waiting_for_edit": waiting_for_edit,
            "session_info": session_info
        }
        
        # Aggiungi dettagli dello stato se disponibile
        if state:
            status_response.update({
                "has_domain": bool(state.get("domain")),
                "has_problem": bool(state.get("problem")),
                "has_messages": bool(state.get("messages")),
                "has_interrupt": bool(state.get("__interrupt__")),
                "user_feedback_provided": state.get("_user_feedback_provided", False),
                "last_user_feedback": state.get("_last_user_feedback")
            })
        
        return jsonify(status_response)
        
    except Exception as e:
        logger.exception("❌ Errore nel controllo stato pipeline")
        return jsonify({
            "error": str(e),
            "thread_id": thread_id,
            "has_state": False,
            "waiting_for_edit": False
        }), 500