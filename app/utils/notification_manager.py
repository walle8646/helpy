"""
Utility per la gestione centralizzata delle notifiche.
Controlla notification_types per decidere se inviare email e/o notifica in-app.
"""
from sqlmodel import select
from app.database import get_session
from app.models import NotificationType, Notification
from app.utils.notification_email import send_notification_email
from loguru import logger
from typing import Dict, Optional


def send_notification(
    notification_type_key: str,
    recipient_user_id: int,
    recipient_email: str,
    recipient_name: str,
    template_data: Dict[str, str],
    related_user_id: Optional[int] = None,
    related_booking_id: Optional[int] = None,
    action_url: Optional[str] = None
) -> bool:
    """
    Invia una notifica controllando i flag di notification_types.
    
    Args:
        notification_type_key: Chiave del tipo notifica (es: 'community_contact')
        recipient_user_id: ID destinatario
        recipient_email: Email destinatario
        recipient_name: Nome destinatario
        template_data: Dati per il template email
        related_user_id: ID utente che ha generato la notifica (opzionale)
        related_booking_id: ID booking correlato (opzionale)
        action_url: URL di azione (opzionale)
    
    Returns:
        bool: True se almeno una notifica è stata inviata con successo
    """
    try:
        with get_session() as session:
            # Trova la configurazione del tipo notifica
            notification_type = session.exec(
                select(NotificationType).where(NotificationType.type_key == notification_type_key)
            ).first()
            
            if not notification_type:
                logger.error(f"❌ Tipo notifica '{notification_type_key}' non trovato in notification_types")
                return False
            
            if not notification_type.is_active:
                logger.info(f"⏭️ Notifica '{notification_type_key}' disabilitata, skip")
                return False
            
            success = False
            
            # 🔔 NOTIFICA IN-APP
            if notification_type.in_app:
                try:
                    # Crea titolo e messaggio dalla template_data
                    title = notification_type.name
                    message = notification_type.description or ""
                    
                    # Se ci sono dati specifici, personalizza il messaggio
                    if 'contact_name' in template_data:
                        message = f"{template_data['contact_name']} vuole contattarti!"
                    elif 'client_name' in template_data:
                        message = f"Nuova prenotazione da {template_data['client_name']}"
                    
                    # Crea una nuova sessione per la notifica
                    with get_session() as notif_session:
                        notification = Notification(
                            user_id=recipient_user_id,
                            type=notification_type_key,
                            title=title,
                            message=message,
                            related_user_id=related_user_id,
                            related_booking_id=related_booking_id,
                            action_url=action_url or "/messages",
                            is_read=False
                        )
                        
                        notif_session.add(notification)
                        notif_session.commit()
                    
                    logger.info(f"🔔 Notifica in-app creata per user {recipient_user_id}: {notification_type_key}")
                    success = True
                    
                except Exception as e:
                    logger.error(f"❌ Errore creazione notifica in-app: {e}")
            
            # 📧 EMAIL
            if notification_type.send_email:
                try:
                    email_sent = send_notification_email(
                        to_email=recipient_email,
                        to_name=recipient_name,
                        subject=notification_type.email_subject or title,
                        template_name=notification_type.email_template,
                        template_data=template_data
                    )
                    
                    if email_sent:
                        logger.info(f"📧 Email notifica inviata a {recipient_email}: {notification_type_key}")
                        success = True
                    else:
                        logger.warning(f"⚠️ Email notifica non inviata a {recipient_email}")
                        
                except Exception as e:
                    logger.error(f"❌ Errore invio email notifica: {e}")
            
            return success
            
    except Exception as e:
        logger.error(f"❌ Errore generale send_notification: {e}")
        return False

