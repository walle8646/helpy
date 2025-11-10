"""
Route per gestione notifiche utente
"""
from fastapi import APIRouter, HTTPException, Request
from sqlmodel import Session, select, func
from app.database import engine
from app.models import Notification, User
from app.routes.auth import get_current_user
from datetime import datetime
from typing import List

router = APIRouter()


@router.get("/api/notifications")
async def get_notifications(request: Request, limit: int = 50, offset: int = 0):
    """Ottiene le notifiche dell'utente corrente"""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    with Session(engine) as session:
        # Query per le notifiche dell'utente
        statement = select(Notification).where(
            Notification.user_id == current_user.id
        ).order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        
        notifications = session.exec(statement).all()
        
        # Formatta le notifiche con i dati dell'utente correlato
        result = []
        for notif in notifications:
            notif_data = {
                "id": notif.id,
                "type": notif.type,
                "title": notif.title,
                "message": notif.message,
                "is_read": notif.is_read,
                "created_at": notif.created_at.isoformat(),
                "action_url": notif.action_url,
                "related_booking_id": notif.related_booking_id
            }
            
            # Aggiungi dati utente correlato se presente
            if notif.related_user_id:
                related_user = session.get(User, notif.related_user_id)
                if related_user:
                    notif_data["related_user"] = {
                        "id": related_user.id,
                        "nome": related_user.nome,
                        "cognome": related_user.cognome,
                        "profile_picture": related_user.profile_picture
                    }
            
            result.append(notif_data)
        
        return result


@router.get("/api/notifications/unread/count")
async def get_unread_notifications_count(request: Request):
    """Ottiene il numero di notifiche non lette"""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    with Session(engine) as session:
        count = session.exec(
            select(func.count(Notification.id)).where(
                Notification.user_id == current_user.id,
                Notification.is_read == False
            )
        ).one()
        
        return {"count": count}


@router.post("/api/notifications/{notification_id}/read")
async def mark_notification_as_read(notification_id: int, request: Request):
    """Segna una notifica come letta"""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    with Session(engine) as session:
        notification = session.get(Notification, notification_id)
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notifica non trovata")
        
        if notification.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Non autorizzato")
        
        notification.is_read = True
        session.add(notification)
        session.commit()
        
        return {"success": True}


@router.post("/api/notifications/read-all")
async def mark_all_notifications_as_read(request: Request):
    """Segna tutte le notifiche come lette"""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    with Session(engine) as session:
        # Ottieni tutte le notifiche non lette
        notifications = session.exec(
            select(Notification).where(
                Notification.user_id == current_user.id,
                Notification.is_read == False
            )
        ).all()
        
        # Segna tutte come lette
        for notification in notifications:
            notification.is_read = True
            session.add(notification)
        
        session.commit()
        
        return {"success": True, "marked_count": len(notifications)}


@router.delete("/api/notifications/{notification_id}")
async def delete_notification(notification_id: int, request: Request):
    """Elimina una notifica"""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    with Session(engine) as session:
        notification = session.get(Notification, notification_id)
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notifica non trovata")
        
        if notification.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Non autorizzato")
        
        session.delete(notification)
        session.commit()
        
        return {"success": True}
