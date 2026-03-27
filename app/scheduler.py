"""
Scheduler per notifiche programmate usando APScheduler.

APScheduler funziona così:
1. BackgroundScheduler: Esegue job in background in un thread separato
2. Job: Attività programmata con una data/ora specifica
3. Trigger: Definisce quando eseguire (date trigger = una volta sola a una data specifica)
4. JobStore: SQLAlchemyJobStore salva i job nel database (sopravvivono ai restart)
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlmodel import Session, select
from app.database import engine
from app.models import Notification, Booking, User, Review
from app.logger_config import logger
from app.utils.notification_service import send_notification
import os

# Timezone italiano
ITALY_TZ = ZoneInfo("Europe/Rome")

# Configurazione APScheduler
jobstores = {
    'default': SQLAlchemyJobStore(url=os.getenv('DATABASE_URL', 'sqlite:///helpy.db'))
}

# Crea lo scheduler (BackgroundScheduler = esegue in un thread separato)
scheduler = BackgroundScheduler(
    jobstores=jobstores,
    timezone=ITALY_TZ  # Tutti i job usano il fuso orario italiano
)


def send_booking_reminder_notification(booking_id: int, user_id: int, is_consultant: bool, minutes_before: int):
    """
    Invia una notifica promemoria per una prenotazione usando il nuovo sistema.
    
    Questa funzione viene eseguita AUTOMATICAMENTE da APScheduler
    al momento programmato (1 ora prima o 10 minuti prima).
    
    Args:
        booking_id: ID della prenotazione
        user_id: ID dell'utente che riceve la notifica
        is_consultant: True se è il consulente, False se è il cliente
        minutes_before: Minuti prima dell'appuntamento (60 o 10)
    """
    try:
        with Session(engine) as session:
            # Carica la prenotazione
            booking = session.get(Booking, booking_id)
            if not booking:
                logger.warning(f"Booking {booking_id} non trovato per notifica reminder")
                return
            
            # Verifica che la prenotazione sia ancora confermata
            if booking.status not in ['confirmed', 'pending']:
                logger.info(f"Booking {booking_id} non è più confermato, skip notifica")
                return
            
            # Carica destinatario e altro utente
            user = session.get(User, user_id)
            other_user_id = booking.consultant_user_id if not is_consultant else booking.client_user_id
            other_user = session.get(User, other_user_id)
            
            if not user or not other_user:
                logger.warning(f"Utente non trovato")
                return
            
            # Determina tipo notifica e dati
            if minutes_before == 60:
                type_key = 'reminder_1h'
                title = "📅 Promemoria Consulenza"
                message = f"La tua consulenza con {other_user.nome} {other_user.cognome} inizia tra 1 ora (alle {booking.start_time})"
                time_label = "1 ora"
            else:
                type_key = 'reminder_10min'
                title = "🔔 Consulenza in Partenza!"
                message = f"La tua consulenza con {other_user.nome} {other_user.cognome} inizia tra 10 minuti! Preparati a confermare la presenza."
                time_label = "10 minuti"
            
            # Formatta la data
            booking_date_str = booking.booking_date.strftime('%d/%m/%Y')
            
            # Invia notifica usando il nuovo sistema (gestisce sia in-app che email)
            send_notification(
                user_id=user_id,
                type_key=type_key,
                title=title,
                message=message,
                template_data={
                    'user_name': user.nome or user.email.split('@')[0],
                    'other_user_name': f"{other_user.nome} {other_user.cognome}" if other_user.nome else other_user.email.split('@')[0],
                    'date': booking_date_str,
                    'time': booking.start_time,
                    'duration': str(booking.duration_minutes),
                    'action_url': f"{os.getenv('BASE_URL', 'http://localhost:8080')}/profile#bookings"
                },
                related_booking_id=booking_id,
                related_user_id=other_user_id,
                action_url=f"/profile?tab=bookings"
            )
            
            logger.info(f"✅ Notifica reminder inviata a user {user_id} per booking {booking_id} ({minutes_before} min prima)")
            
    except Exception as e:
        logger.error(f"❌ Errore nell'invio notifica reminder: {e}")


def schedule_booking_reminders(booking_id: int, booking_datetime: datetime, client_id: int, consultant_id: int):
    """
    Schedula le notifiche promemoria per una prenotazione.
    
    Questa funzione viene chiamata SUBITO DOPO che una prenotazione è confermata.
    Crea 4 job totali:
    - 2 job per il cliente (1 ora prima + 10 min prima)
    - 2 job per il consulente (1 ora prima + 10 min prima)
    
    Args:
        booking_id: ID della prenotazione
        booking_datetime: Data e ora della prenotazione (timezone-aware)
        client_id: ID del cliente
        consultant_id: ID del consulente
    """
    try:
        # Assicurati che booking_datetime sia timezone-aware (Italia)
        if booking_datetime.tzinfo is None:
            booking_datetime = booking_datetime.replace(tzinfo=ITALY_TZ)
        
        # Calcola i momenti per le notifiche
        one_hour_before = booking_datetime - timedelta(hours=1)
        ten_minutes_before = booking_datetime - timedelta(minutes=10)
        
        # Non schedulare se è troppo tardi (già passato)
        now = datetime.now(ITALY_TZ)
        
        # Schedula notifiche 1 ora prima (se non è troppo tardi)
        if one_hour_before > now:
            # Notifica al cliente
            scheduler.add_job(
                send_booking_reminder_notification,
                trigger=DateTrigger(run_date=one_hour_before),
                args=[booking_id, client_id, False, 60],
                id=f"reminder_client_60_{booking_id}",
                replace_existing=True,  # Se esiste già, lo sostituisce
                misfire_grace_time=300  # Tollera 5 minuti di ritardo
            )
            
            # Notifica al consulente
            scheduler.add_job(
                send_booking_reminder_notification,
                trigger=DateTrigger(run_date=one_hour_before),
                args=[booking_id, consultant_id, True, 60],
                id=f"reminder_consultant_60_{booking_id}",
                replace_existing=True,
                misfire_grace_time=300
            )
            
            logger.info(f"📅 Schedulata notifica 1h prima per booking {booking_id} alle {one_hour_before}")
        
        # Schedula notifiche 10 minuti prima (se non è troppo tardi)
        if ten_minutes_before > now:
            # Notifica al cliente
            scheduler.add_job(
                send_booking_reminder_notification,
                trigger=DateTrigger(run_date=ten_minutes_before),
                args=[booking_id, client_id, False, 10],
                id=f"reminder_client_10_{booking_id}",
                replace_existing=True,
                misfire_grace_time=300
            )
            
            # Notifica al consulente
            scheduler.add_job(
                send_booking_reminder_notification,
                trigger=DateTrigger(run_date=ten_minutes_before),
                args=[booking_id, consultant_id, True, 10],
                id=f"reminder_consultant_10_{booking_id}",
                replace_existing=True,
                misfire_grace_time=300
            )
            
            logger.info(f"🔔 Schedulata notifica 10min prima per booking {booking_id} alle {ten_minutes_before}")
        
    except Exception as e:
        logger.error(f"❌ Errore nello scheduling notifiche per booking {booking_id}: {e}")


def send_review_reminder_notification(booking_id: int, client_id: int, review_token: str):
    """
    Invia un promemoria via email per lasciare una recensione.
    Eseguita automaticamente 24h dopo la richiesta.
    """
    try:
        with Session(engine) as session:
            # Controlla se la recensione è già stata fatta
            existing = session.exec(
                select(Review).where(Review.booking_id == booking_id)
            ).first()
            if existing:
                logger.info(f"Review già presente per booking {booking_id}, skip reminder")
                return

            booking = session.get(Booking, booking_id)
            if not booking:
                return

            client = session.get(User, client_id)
            consultant = session.get(User, booking.consultant_user_id)
            if not client or not consultant:
                return

            consultant_name = f"{consultant.nome} {consultant.cognome}" if consultant.nome else consultant.email.split('@')[0]
            base_url = os.getenv('BASE_URL', 'http://localhost:8080')
            review_url = f"{base_url}/review/{review_token}?booking_id={booking_id}"
            booking_date_str = booking.booking_date.strftime('%d/%m/%Y')

            send_notification(
                user_id=client_id,
                type_key='review_reminder',
                title='Ricordati di lasciare una recensione',
                message=f'Non hai ancora recensito la tua consulenza con {consultant_name}',
                template_data={
                    'user_name': client.nome or client.email.split('@')[0],
                    'consultant_name': consultant_name,
                    'review_url': review_url,
                    'date': booking_date_str,
                    'time': booking.start_time,
                },
                related_booking_id=booking_id,
                action_url=review_url
            )

            logger.info(f"🔔 Promemoria recensione inviato a user {client_id} per booking {booking_id}")

    except Exception as e:
        logger.error(f"❌ Errore invio promemoria recensione: {e}")


def schedule_review_reminder(booking_id: int, client_id: int, review_token: str, run_date: datetime):
    """
    Schedula un promemoria per la recensione a 24h.
    """
    try:
        scheduler.add_job(
            send_review_reminder_notification,
            trigger=DateTrigger(run_date=run_date),
            args=[booking_id, client_id, review_token],
            id=f"review_reminder_{booking_id}",
            replace_existing=True,
            misfire_grace_time=3600  # 1 ora di tolleranza
        )
        logger.info(f"📅 Schedulato promemoria recensione per booking {booking_id} alle {run_date}")
    except Exception as e:
        logger.error(f"❌ Errore scheduling promemoria recensione: {e}")


def start_scheduler():
    """
    Avvia lo scheduler.
    Chiamata all'avvio dell'applicazione (in main.py).
    """
    if not scheduler.running:
        scheduler.start()
        logger.info("🚀 APScheduler avviato con successo")


def shutdown_scheduler():
    """
    Ferma lo scheduler in modo pulito.
    Chiamata alla chiusura dell'applicazione.
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 APScheduler fermato")
