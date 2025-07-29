from __future__ import annotations
import os
import json
import logging
import shutil
from pathlib import Path
from typing import cast, Any, Dict, Optional, Generator
from flask import Blueprint, request, jsonify, url_for, Response, stream_with_context
from flask.typing import ResponseReturnValue
from langchain_core.messages import HumanMessage, BaseMessage
from graphs.pddl_pipeline_graph import get_pipeline_with_memory, PipelineState
from langgraph.types import Interrupt
from langchain_core.runnables.config import RunnableConfig
from db.schema import Base, GenerationSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

_graph_cache: Dict[str, Any] = {}

pipeline_chat_bp = Blueprint("pipeline_chat", __name__)
logger = logging.getLogger(__name__)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

def get_db_session(thread_id: str) -> Session:
    """Crea una sessione database per GenerationSession"""
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

def get_pipeline_state_from_langgraph(thread_id: str) -> Optional[Dict[str, Any]]:
    """Ottiene lo stato corrente SOLO da LangGraph"""
    try:
        graph = get_pipeline_with_memory(thread_id, reset=False)
        
        config: RunnableConfig = {
            "configurable": {"thread_id": thread_id}
        }
        
        state_snapshot = graph.get_state(config)
        
        if state_snapshot and state_snapshot.values:
            return dict(state_snapshot.values)
            
    except Exception as e:
        logger.error("Errore lettura stato LangGraph: %s", e)
    
    return None

def update_generation_session(thread_id: str, **kwargs) -> None:
    """Aggiorna o crea una sessione di generazione - SOLO per logging/tracking"""
    try:
        db_session = get_db_session(thread_id)
        try:
            session = db_session.query(GenerationSession)\
                .filter_by(session_id=thread_id)\
                .first()
            
            if not session:
                session = GenerationSession(session_id=thread_id)
                db_session.add(session)
            
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

def apply_user_feedback(thread_id: str, domain: str, problem: str, user_message: Optional[str] = None) -> Dict[str, Any]:
    """
    Applica il feedback dell'utente allo stato LangGraph e riprende la pipeline.
    
    Args:
        thread_id: ID del thread
        domain: Dominio PDDL modificato dall'utente
        problem: Problema PDDL modificato dall'utente
        user_message: Messaggio opzionale dell'utente
    
    Returns:
        Risultato dell'esecuzione della pipeline
    """
    try:
        graph = get_pipeline_with_memory(thread_id, reset=False)
        
        config: RunnableConfig = {
            "configurable": {"thread_id": thread_id}
        }
        
        current_state = graph.get_state(config)
        if not current_state or not current_state.values:
            raise ValueError(f"Nessuno stato trovato per thread_id: {thread_id}")
        
        state_values = dict(current_state.values)
        tmp_dir = state_values.get("tmp_dir")
        if tmp_dir:
            edited_dir = os.path.join(tmp_dir, "edited")
            os.makedirs(edited_dir, exist_ok=True)
            
            domain_path = os.path.join(edited_dir, "domain.pddl")
            problem_path = os.path.join(edited_dir, "problem.pddl")
            
            with open(domain_path, "w", encoding="utf-8") as f:
                f.write(domain)
            with open(problem_path, "w", encoding="utf-8") as f:
                f.write(problem)
            
            logger.info("✅ PDDL editati salvati in: %s", edited_dir)
        
        updated_state = dict(current_state.values)
        updated_state.update({
            "domain": domain,
            "problem": problem,
            "_waiting_for_edit": False,
            "_resume_after_feedback": True,
        })
        
        if user_message:
            messages = updated_state.get("messages", [])
            messages.append(HumanMessage(content=user_message))
            updated_state["messages"] = messages
        
        graph.update_state(config, updated_state)
        
        logger.info("✅ Stato LangGraph aggiornato con PDDL editati per thread: %s", thread_id)
        
        empty_state: PipelineState = cast(PipelineState, {
            "messages": [],
            "thread_id": thread_id
        })
        result = graph.invoke(empty_state, config=config)
        
        logger.info("✅ Pipeline ripresa dopo feedback per thread: %s", thread_id)
        return result
        
    except Exception as e:
        logger.error("❌ Errore applicazione feedback: %s", e)
        raise

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

        graph = get_pipeline_with_memory(thread_id, reset=reset)

        if reset:
            logger.info("🔄 Reset esplicito richiesto per thread: %s", thread_id)
            
            _graph_cache.pop(thread_id, None)
            
            mem_db = f"memory/{thread_id}.sqlite"
            if os.path.exists(mem_db):
                os.remove(mem_db)
                logger.info("🧹 Database LangGraph rimosso: %s", mem_db)
            
            tmp_dir = os.path.join("static", "uploads", thread_id)
            if os.path.exists(tmp_dir):
                import shutil
                shutil.rmtree(tmp_dir)
                logger.info("🧹 Directory temporanea rimossa: %s", tmp_dir)
            
            graph = get_pipeline_with_memory(thread_id, reset=True)
            
            if not data.get("message") and not data.get("lore"):
                return jsonify({
                    "response": "✅ Pipeline resettata con successo.",
                    "status": "reset_completed",
                    "thread_id": thread_id
                })

        if "domain" in data and "problem" in data:
            logger.info("✍️ Resume con domain/problem modificati")
            
            result = apply_user_feedback(
                thread_id, 
                data["domain"], 
                data["problem"], 
                data.get("message")
            )

        elif "message" in data:
            logger.info("💬 Messaggio testuale ricevuto")
            
            user_message = HumanMessage(content=data["message"])
            message_state: PipelineState = cast(PipelineState, {
                "messages": [user_message],
                "thread_id": thread_id,
                "_explicit_reset": reset 
            })
            
            result = graph.invoke(message_state, config=config)

        else:
            logger.info("⚡ Avvio pipeline completa")
            
            lore_dict = load_lore(data.get("lore"), data.get("custom_story"))
            
            initial_state: PipelineState = cast(PipelineState, {
                "thread_id": thread_id,
                "lore": lore_dict,
                "messages": [],
                "config": lore_dict,
                "_explicit_reset": reset
            })
            
            result = graph.invoke(initial_state, config=config)
            
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

        response_text: Optional[str] = None
        for msg in result.get("messages", []):
            if isinstance(msg, dict) and msg.get("type") == "ai":
                response_text = str(msg["content"])
                break

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

@pipeline_chat_bp.route("/feedback", methods=["POST"])
def handle_feedback() -> ResponseReturnValue:
    """Endpoint dedicato per ricevere e applicare feedback PDDL dall'utente"""
    print(">>> /feedback chiamata")
    try:
        data: Dict[str, Any] = request.get_json(force=True) or {}
        print(f">>> feedback payload: {data}")
        thread_id = data.get("thread_id")
        domain = data.get("domain")
        problem = data.get("problem")
        user_message = data.get("message", "")

        print("\nEdited Domain:\n", domain)
        print("\nEdited Problem:\n", problem)

        if thread_id is None:
            return jsonify({"error": "thread assente."})

        state = get_pipeline_state_from_langgraph(thread_id)
        if state is None:
            return jsonify({"error": "Impossibile recuperare lo stato della pipeline."}), 400

        if domain is None or problem is None:
            return jsonify({"error": "domain, problem assenti."}), 400
        
        tmp_dir = state.get("tmp_dir")
        if not tmp_dir:
            return jsonify({"error": "tmp_dir non disponibile nello stato."}), 400
        os.makedirs(tmp_dir, exist_ok=True)
        edited_dir = os.path.join(tmp_dir, "edited")
        os.makedirs(edited_dir, exist_ok=True)

        domain_path  = os.path.join(edited_dir, "domain.pddl")
        problem_path = os.path.join(edited_dir, "problem.pddl")
        with open(domain_path,  "w", encoding="utf-8") as f:
            f.write(domain)
        with open(problem_path, "w", encoding="utf-8") as f:
            f.write(problem)
        print(f"[DBG][chat_feedback] Saved edited PDDL to {domain_path} and {problem_path}")

        
        if not thread_id:
            return jsonify({"error": "thread_id è richiesto"}), 400
        if not domain or not problem:
            return jsonify({"error": "domain e problem sono richiesti"}), 400
        
        logger.info("📝 Feedback ricevuto per thread: %s", thread_id)
        
        result = apply_user_feedback(thread_id, domain, problem, user_message)
        
        response_text: Optional[str] = None
        for msg in result.get("messages", []):
            if isinstance(msg, dict) and msg.get("type") == "ai":
                response_text = str(msg["content"])
                break
        
        urls = copy_generated_files(result, thread_id)
        
        update_generation_session(
            thread_id,
            domain=result.get("domain"),
            problem=result.get("problem"),
            validation=result.get("validation"),
            refined_domain=result.get("refined_domain"),
            refined_problem=result.get("refined_problem")
        )
        
        return jsonify({
            "status": "feedback_applied",
            "response": response_text or "✅ Feedback applicato con successo.",
            "validation": result.get("validation"),
            "refined_domain": result.get("refined_domain"),
            "refined_problem": result.get("refined_problem"),
            **urls
        })
        
    except Exception as e:
        logger.exception("❌ Errore applicazione feedback")
        return jsonify({"error": str(e)}), 500

@pipeline_chat_bp.route("/stream", methods=["GET"])
def stream_pipeline() -> ResponseReturnValue:
    """Endpoint per streaming della pipeline (GET)"""
    try:
        thread_id = request.args.get("thread_id", "session-1")
        lore_param = request.args.get("lore")
        custom_story = request.args.get("custom_story")
        reset = request.args.get("reset", "false").lower() == "true"
        resume = request.args.get("resume", "false").lower() == "true"

        config: RunnableConfig = {
            "configurable": {"thread_id": thread_id}
        }

        logger.info("🎬 Stream request - thread_id: %s, reset: %s", thread_id, reset)

        if reset:
            logger.info("🔄 Reset esplicito per stream thread: %s", thread_id)
            
            _graph_cache.pop(thread_id, None)
            
        elif not resume:
            current_state = get_pipeline_state_from_langgraph(thread_id)
            waiting_for_edit = current_state and current_state.get("_waiting_for_edit", False) if current_state is not None else False
            
            if waiting_for_edit:
                logger.info("✋ Pipeline in attesa di editing, invio stato corrente")
                
                def edit_resume_stream() -> Generator[str, None, None]:
                    try:
                        if current_state is None:
                            yield f"event: error\ndata: {json.dumps({'message': 'Stato non disponibile'}, ensure_ascii=False)}\n\n"
                            return
                            
                        domain = current_state.get("domain", "")
                        problem = current_state.get("problem", "")
                        
                        if current_state.get("refined_domain"):
                            domain = current_state["refined_domain"]
                        if current_state.get("refined_problem"):
                            problem = current_state["refined_problem"]
                        
                        payload = {
                            "domain": domain,
                            "problem": problem,
                            "status": current_state.get("status", "waiting_for_edit")
                        }
                        
                        yield f"event: ChatFeedback\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                        yield "event: PauseForFeedback\ndata: {}\n\n"
                        yield "event: stream_paused\ndata: {}\n\n"
                        
                    except Exception as e:
                        logger.exception("Errore durante edit resume stream")
                        yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"

                return Response(
                    stream_with_context(edit_resume_stream()), 
                    mimetype="text/event-stream",
                    headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive'}
                )

        lore_dict = load_lore(lore_param, custom_story)
        
        graph = get_pipeline_with_memory(thread_id, reset=reset)
        
        def unified_event_stream() -> Generator[str, None, None]:
            """Generator unificato per Server-Sent Events con stato preservato"""
            try:
                current_state = get_pipeline_state_from_langgraph(thread_id)
                
                initial_state: PipelineState = cast(PipelineState, {
                    "thread_id": thread_id,
                    "lore": lore_dict,
                    "messages": [],
                    "config": lore_dict,
                    "_explicit_reset": reset
                })
                
                if current_state:
                    logger.info("🔄 Stato LangGraph esistente trovato, preservando dati critici")
                    
                    if current_state.get("_resume_after_feedback"):
                        initial_state["_resume_after_feedback"] = True
                        logger.info("✅ Flag _resume_after_feedback preservato")
                    
                    if current_state.get("_waiting_for_edit"):
                        initial_state["_waiting_for_edit"] = True
                        logger.info("✅ Flag _waiting_for_edit preservato")
                    
                    if current_state.get("tmp_dir"):
                        initial_state["tmp_dir"] = current_state["tmp_dir"]
                        logger.info("✅ tmp_dir preservata: %s", current_state["tmp_dir"])
                    
                    tmp_dir = current_state.get("tmp_dir")
                    if tmp_dir:
                        edited_dir = os.path.join(tmp_dir, "edited")
                        if os.path.isdir(edited_dir):
                            dom_edited = os.path.join(edited_dir, "domain.pddl")
                            prob_edited = os.path.join(edited_dir, "problem.pddl")
                            
                            if os.path.exists(dom_edited) and os.path.exists(prob_edited):
                                try:
                                    with open(dom_edited, "r", encoding="utf-8") as f:
                                        edited_domain = f.read().strip()
                                    with open(prob_edited, "r", encoding="utf-8") as f:
                                        edited_problem = f.read().strip()
                                    
                                    if edited_domain and edited_problem:
                                        initial_state["domain"] = edited_domain
                                        initial_state["problem"] = edited_problem
                                        logger.info("✅ PDDL editati caricati da %s", edited_dir)
                                except Exception as e:
                                    logger.warning("⚠ Errore caricamento PDDL editati: %s", e)
                    
                    for key in ["status", "attempt", "validation", "refined_domain", "refined_problem"]:
                        if current_state.get(key) is not None:
                            initial_state[key] = current_state[key]
                
                logger.info("🚀 Avvio stream per thread: %s", thread_id)
                
                pipeline_paused = False
        
                for chunk in graph.stream(initial_state, config=config):
                    chunk_events = list(process_stream_chunk(chunk, thread_id))
                    
                    for event_line in chunk_events:
                        if "event: pause_for_editing" in event_line:
                            pipeline_paused = True
                            
                    for event_line in chunk_events:
                        yield event_line
                    
                    if pipeline_paused:
                        logger.info("🛑 Pipeline in pausa, connessione mantenuta aperta")
                        return
                
                yield "event: done\ndata: {}\n\n"
                
            except StopIteration:
                yield "event: done\ndata: {}\n\n"
            except Exception as e:
                logger.exception("Errore in unified_event_stream")
                yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"
                yield "event: done\ndata: {}\n\n"

        return Response(
            stream_with_context(unified_event_stream()), 
            mimetype="text/event-stream",
            headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive'}
        )

    except (ValueError, FileNotFoundError) as e:
        logger.error("❌ Errore validazione stream: %s", str(e))
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("❌ Errore generale stream")
        return jsonify({"error": str(e)}), 500

def process_stream_chunk(chunk: Dict[str, Any], thread_id: str) -> Generator[str, None, None]:
    """Processa un singolo chunk dello stream"""
    try:
        chunk_data = {}
        for key in ["domain", "problem", "validation", "refined_domain", "refined_problem"]:
            if key in chunk:
                chunk_data[key] = chunk[key]
        
        state = get_pipeline_state_from_langgraph(thread_id)
        if state and "lore" in state:
            chunk_data["lore"] = state["lore"]

        if chunk_data:
            update_generation_session(thread_id, **chunk_data)

        if "prompt" in chunk:
            logger.info("📝 [SSE] Emettendo evento prompt")
            prompt_payload = {
                "prompt": chunk["prompt"],
                "status": "prompt_generated"
            }
            yield f"event: prompt\ndata: {json.dumps(prompt_payload, ensure_ascii=False)}\n\n"
        
        if "plan" in chunk:
            logger.info("🎯 [SSE] chunk contiene piano! Emissione GeneratePlan...")
            payload = {
                "plan": chunk["plan"],
                "plan_log": chunk.get("plan_log"),
                "plan_url": chunk.get("plan_url"),
                "status": chunk.get("status", "success"),
                "found_plan": True,
                "pipeline_completing": True
            }
            yield f"event: GeneratePlan\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            logger.info("✅ [SSE] GeneratePlan emesso")

        if "__interrupt__" in chunk:
            interrupt_item = chunk["__interrupt__"]
            interrupt_obj: Optional[Interrupt] = None
            
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
                
                if isinstance(payload, dict) and "domain" in payload and "problem" in payload:
                    logger.info("🛑 Interruzione stream per editing")
                    
                    yield f"event: ChatFeedback\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    yield "event: PauseForFeedback\ndata: {}\n\n"
                    yield "event: stream_paused\ndata: {}\n\n"
                    return
                else:
                    logger.info("📊 Interruzione di stato normale")
                    yield f"event: status_interrupt\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

        for key, val in chunk.items():
            if key not in ["__interrupt__", "plan"]:
                logger.info(f"📤 [SSE] Emettendo evento: {key}")
                yield f"event: {key}\ndata: {json.dumps(serialize_value(val), ensure_ascii=False)}\n\n"
                
    except Exception as e:
        logger.exception("❌ Errore processamento chunk")
        yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"

@pipeline_chat_bp.route("/resume", methods=["POST"])
def resume_pipeline() -> ResponseReturnValue:
    """Endpoint legacy per compatibilità - redirige a /feedback"""
    try:
        data: Dict[str, Any] = request.get_json(force=True) or {}
        
        return handle_feedback()

    except Exception as e:
        logger.exception("❌ Errore nel resume legacy")
        return jsonify({"error": str(e)}), 500

@pipeline_chat_bp.route("/status/<thread_id>", methods=["GET"])
def get_pipeline_status(thread_id: str) -> ResponseReturnValue:
    """Endpoint per controllare lo stato della pipeline - SOLO tramite LangGraph"""
    try:
        state = get_pipeline_state_from_langgraph(thread_id)
        
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
                        "created_at": session.created_at.isoformat() if session.created_at else None
                    }
            finally:
                db_session.close()
        except Exception as e:
            logger.error("Errore lettura GenerationSession: %s", e)
            session_info = {"error": str(e)}
        
        status_response = {
            "thread_id": thread_id,
            "has_state": bool(state),
            "session_info": session_info
        }
        
        if state:
            status_response.update({
                "status": state.get("status", "unknown"),
                "waiting_for_edit": state.get("_waiting_for_edit", False),
                "resume_after_feedback": state.get("_resume_after_feedback", False),
                "has_domain": bool(state.get("domain")),
                "has_problem": bool(state.get("problem")),
                "has_refined_domain": bool(state.get("refined_domain")),
                "has_refined_problem": bool(state.get("refined_problem")),
                "has_messages": bool(state.get("messages")),
                "has_validation": bool(state.get("validation")),
                "lore_id": state.get("lore", {}).get("id") if state.get("lore") else None
            })
        else:
            status_response.update({
                "status": "no_state",
                "waiting_for_edit": False,
                "resume_after_feedback": False,
                "has_domain": False,
                "has_problem": False,
                "has_refined_domain": False,
                "has_refined_problem": False,
                "has_messages": False,
                "has_validation": False,
                "lore_id": None
            })
        
        return jsonify(status_response)
        
    except Exception as e:
        logger.exception("❌ Errore nel controllo stato pipeline")
        return jsonify({
            "error": str(e),
            "thread_id": thread_id,
            "has_state": False,
            "status": "error",
            "waiting_for_edit": False
        }), 500