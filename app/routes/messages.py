from fastapi import APIRouter, Request, Form, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.database import get_session
from app.models import User, Conversation, Message
from sqlmodel import select, or_, and_, func
from datetime import datetime
from app.logger_config import logger
from typing import Optional

# ✅ Importa funzioni autenticazione da auth.py
from app.routes.auth import verify_token, get_current_user

router = APIRouter()

# ========== CONFIGURAZIONE LIMITI ==========
MAX_MESSAGES_PER_CONVERSATION = 80  # ✅ Modificato da 1000 a 80
MAX_MESSAGE_LENGTH = 1000

# ========== API ENDPOINTS ==========

@router.get("/api/current-user")
async def api_get_current_user(request: Request):
    """API endpoint to get current logged-in user info"""
    user = verify_token(request)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    return JSONResponse({
        "id": user.id,
        "email": user.email,
        "nome": user.nome,
        "cognome": user.cognome,
        "is_verified": user.is_verified,
        "category_id": user.category_id
    })

# ========== HELPER FUNCTIONS ==========

def get_or_create_conversation(session, user1_id: int, user2_id: int) -> Conversation:
    """Ottieni conversazione esistente o creane una nuova"""
    min_id = min(user1_id, user2_id)
    max_id = max(user1_id, user2_id)
    
    conversation = session.exec(
        select(Conversation).where(
            and_(
                Conversation.user1_id == min_id,
                Conversation.user2_id == max_id
            )
        )
    ).first()
    
    if not conversation:
        conversation = Conversation(
            user1_id=min_id,
            user2_id=max_id
        )
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
        logger.info(f"✅ New conversation created: {min_id} <-> {max_id}")
    
    return conversation

# ========== PAGINA LISTA CONVERSAZIONI ==========

@router.get("/messaggi", response_class=HTMLResponse)
async def messages_inbox_page(request: Request):
    """Pagina inbox con lista conversazioni"""
    current_user = verify_token(request)
    
    if not current_user:
        return RedirectResponse("/login?redirect=/messaggi", status_code=302)
    
    logger.info(f"📧 Inbox - User: {current_user.nome} (ID: {current_user.id})")
    
    return request.app.state.templates.TemplateResponse(
        "messages_inbox.html",
        {
            "request": request,
            "user": current_user  # ✅ USA "user" come in profile.py
        }
    )

# ========== PAGINA CHAT CON UTENTE SPECIFICO ==========

@router.get("/messaggi/{other_user_id}", response_class=HTMLResponse)
async def chat_page(request: Request, other_user_id: int):
    """Pagina chat con un altro utente"""
    current_user = verify_token(request)
    
    if not current_user:
        return RedirectResponse(f"/login?redirect=/messaggi/{other_user_id}", status_code=302)
    
    with get_session() as session:
        other_user = session.get(User, other_user_id)
        
        if not other_user:
            raise HTTPException(status_code=404, detail="Utente non trovato")
        
        if current_user.id == other_user_id:
            raise HTTPException(status_code=400, detail="Non puoi chattare con te stesso")
        
        logger.info(f"💬 Chat: {current_user.nome} -> {other_user.nome}")
        
        return request.app.state.templates.TemplateResponse(
            "chat.html",
            {
                "request": request,
                "user": current_user,  # ✅ USA "user"
                "other_user": other_user
            }
        )

# ========== API: Lista Conversazioni ==========

@router.get("/api/conversations")
async def get_conversations(request: Request):
    """Ottieni lista conversazioni dell'utente loggato"""
    # ✅ Usa verify_token da auth.py
    current_user = verify_token(request)
    
    if not current_user:
        return JSONResponse({"error": "Non autenticato"}, status_code=401)
    
    try:
        with get_session() as session:
            user_id = current_user.id
            
            conversations = session.exec(
                select(Conversation)
                .where(
                    or_(
                        Conversation.user1_id == user_id,
                        Conversation.user2_id == user_id
                    )
                )
                .order_by(Conversation.updated_at.desc())
            ).all()
            
            result = []
            for conv in conversations:
                other_user_id = conv.user2_id if conv.user1_id == user_id else conv.user1_id
                other_user = session.get(User, other_user_id)
                
                if not other_user:
                    continue
                
                last_message = session.exec(
                    select(Message)
                    .where(Message.conversation_id == conv.id)
                    .order_by(Message.created_at.desc())
                    .limit(1)
                ).first()
                
                unread_count = session.exec(
                    select(func.count())
                    .select_from(Message)
                    .where(
                        and_(
                            Message.conversation_id == conv.id,
                            Message.sender_id != user_id,
                            Message.is_read == False
                        )
                    )
                ).one()
                
                result.append({
                    "conversation_id": conv.id,
                    "other_user": {
                        "id": other_user.id,
                        "nome": other_user.nome or "Utente",
                        "cognome": other_user.cognome or "",
                        "profile_picture": other_user.profile_picture or None,
                        "professione": other_user.professione or ""
                    },
                    "last_message": {
                        "id": last_message.id if last_message else None,  # ✅ Aggiunto ID
                        "content": last_message.content if last_message else None,
                        "created_at": last_message.created_at.isoformat() if last_message else None,
                        "is_mine": last_message.sender_id == user_id if last_message else False,
                        "is_sender": last_message.sender_id == user_id if last_message else False  # ✅ Aggiunto is_sender
                    } if last_message else None,
                    "unread_count": unread_count,
                    "updated_at": conv.updated_at.isoformat()
                })
            
            logger.info(f"✅ Loaded {len(result)} conversations for user {user_id}")
            return JSONResponse({"conversations": result}, status_code=200)
    
    except Exception as e:
        logger.error(f"Error getting conversations: {e}", exc_info=True)
        return JSONResponse({"error": "Errore caricamento conversazioni"}, status_code=500)

# ========== API: Ottieni Messaggi ==========

@router.get("/api/messaggi/{other_user_id}")
async def get_messages(
    request: Request,
    other_user_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100)
):
    """Ottieni messaggi di una conversazione"""
    current_user = verify_token(request)
    
    if not current_user:
        return JSONResponse({"error": "Non autenticato"}, status_code=401)
    
    try:
        with get_session() as session:
            user_id = current_user.id
            
            conversation = get_or_create_conversation(session, user_id, other_user_id)
            
            # ✅ Ottieni gli ultimi 100 messaggi (modificato da 15)
            messages = session.exec(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.created_at.desc())
                .limit(100)  # ✅ Carica ultimi 100 messaggi
            ).all()
            
            # Conta messaggi totali
            total_messages = session.exec(
                select(func.count())
                .select_from(Message)
                .where(Message.conversation_id == conversation.id)
            ).one()
            
            # Marca messaggi come letti
            unread_messages = session.exec(
                select(Message)
                .where(
                    and_(
                        Message.conversation_id == conversation.id,
                        Message.sender_id == other_user_id,
                        Message.is_read == False
                    )
                )
            ).all()
            
            for msg in unread_messages:
                msg.is_read = True
                session.add(msg)
            
            if unread_messages:
                session.commit()
                logger.info(f"✅ Marked {len(unread_messages)} messages as read")
            
            result = [
                {
                    "id": msg.id,
                    "content": msg.content,
                    "sender_id": msg.sender_id,
                    "is_sender": msg.sender_id == user_id,  # ✅ Rinominato da is_mine a is_sender per il frontend
                    "is_mine": msg.sender_id == user_id,  # ✅ Mantenuto per backward compatibility
                    "is_system_message": msg.is_system_message if hasattr(msg, 'is_system_message') else False,  # ✅ Aggiunto per messaggi di sistema
                    "created_at": msg.created_at.isoformat(),
                    "is_read": msg.is_read
                }
                for msg in reversed(messages)
            ]
            
            logger.info(f"✅ Loaded {len(result)}/{total_messages} messages for conversation {conversation.id}")
            
            return JSONResponse({
                "messages": result,
                "total": total_messages,
                "showing": len(result),
                "has_more": total_messages > 100  # ✅ Indica se ci sono più di 100 messaggi
            }, status_code=200)
    
    except Exception as e:
        logger.error(f"Error getting messages: {e}", exc_info=True)
        return JSONResponse({"error": "Errore caricamento messaggi"}, status_code=500)

# ========== API: Invia Messaggio ==========

@router.post("/api/messaggi/{other_user_id}")
async def send_message(
    request: Request,
    other_user_id: int,
    content: str = Form(...)
):
    """Invia un messaggio"""
    current_user = verify_token(request)
    
    if not current_user:
        return JSONResponse({"error": "Non autenticato"}, status_code=401)
    
    # ✅ VALIDAZIONE LUNGHEZZA
    if not content or len(content.strip()) == 0:
        return JSONResponse({"error": "Messaggio vuoto"}, status_code=400)
    
    if len(content) > MAX_MESSAGE_LENGTH:
        return JSONResponse({
            "error": f"Messaggio troppo lungo (max {MAX_MESSAGE_LENGTH} caratteri)"
        }, status_code=400)
    
    try:
        with get_session() as session:
            user_id = current_user.id
            
            other_user = session.get(User, other_user_id)
            if not other_user:
                return JSONResponse({"error": "Utente non trovato"}, status_code=404)
            
            if user_id == other_user_id:
                return JSONResponse({"error": "Non puoi inviare messaggi a te stesso"}, status_code=400)
            
            conversation = get_or_create_conversation(session, user_id, other_user_id)
            
            # ✅ VERIFICA LIMITE MESSAGGI
            message_count = session.exec(
                select(func.count())
                .select_from(Message)
                .where(Message.conversation_id == conversation.id)
            ).one()
            
            if message_count >= MAX_MESSAGES_PER_CONVERSATION:
                return JSONResponse({
                    "error": f"Limite di {MAX_MESSAGES_PER_CONVERSATION} messaggi raggiunto per questa conversazione"
                }, status_code=400)
            
            # ✅ CREA MESSAGGIO
            message = Message(
                conversation_id=conversation.id,
                sender_id=user_id,
                content=content.strip(),
                is_read=False
            )
            session.add(message)
            
            conversation.updated_at = datetime.utcnow()
            session.add(conversation)
            
            session.commit()
            session.refresh(message)
            
            logger.info(f"✅ Message sent: {current_user.nome} (#{user_id}) -> {other_user.nome} (#{other_user_id}) [{message_count + 1}/{MAX_MESSAGES_PER_CONVERSATION}]")
            
            return JSONResponse({
                "success": True,
                "message": {
                    "id": message.id,
                    "content": message.content,
                    "created_at": message.created_at.isoformat(),
                    "is_mine": True
                },
                "messages_left": MAX_MESSAGES_PER_CONVERSATION - message_count - 1
            }, status_code=201)
    
    except Exception as e:
        logger.error(f"Error sending message: {e}", exc_info=True)
        return JSONResponse({"error": "Errore invio messaggio"}, status_code=500)

# ========== API: Elimina Messaggio ==========

@router.delete("/api/messaggi/{message_id}")
async def delete_message(request: Request, message_id: int):
    """Elimina un messaggio (solo il mittente può eliminare)"""
    # ✅ Usa verify_token da auth.py
    current_user = verify_token(request)
    
    if not current_user:
        return JSONResponse({"error": "Non autenticato"}, status_code=401)
    
    try:
        with get_session() as session:
            message = session.get(Message, message_id)
            
            if not message:
                return JSONResponse({"error": "Messaggio non trovato"}, status_code=404)
            
            if message.sender_id != current_user.id:
                return JSONResponse({"error": "Non autorizzato"}, status_code=403)
            
            session.delete(message)
            session.commit()
            
            logger.info(f"✅ Message {message_id} deleted by user {current_user.id}")
            
            return JSONResponse({"success": True}, status_code=200)
    
    except Exception as e:
        logger.error(f"Error deleting message: {e}", exc_info=True)
        return JSONResponse({"error": "Errore eliminazione messaggio"}, status_code=500)

# ========== API: Conta Messaggi Non Letti Totali ==========

@router.get("/api/unread-count")
async def get_unread_count(request: Request):
    """Ottieni conteggio totale messaggi non letti"""
    # ✅ Usa verify_token da auth.py
    current_user = verify_token(request)
    
    if not current_user:
        return JSONResponse({"error": "Non autenticato"}, status_code=401)
    
    try:
        with get_session() as session:
            user_id = current_user.id
            
            unread_count = session.exec(
                select(func.count())
                .select_from(Message)
                .join(Conversation)
                .where(
                    and_(
                        or_(
                            Conversation.user1_id == user_id,
                            Conversation.user2_id == user_id
                        ),
                        Message.sender_id != user_id,
                        Message.is_read == False
                    )
                )
            ).one()
            
            return JSONResponse({"unread_count": unread_count}, status_code=200)
    
    except Exception as e:
        logger.error(f"Error getting unread count: {e}", exc_info=True)
        return JSONResponse({"error": "Errore conteggio messaggi"}, status_code=500)