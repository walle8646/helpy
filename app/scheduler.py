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
from apscheduler.jobstores.base import JobLookupError
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlmodel import Session, select
from app.database import engine
from app.models import Notification, Booking, User, Review, Dispute
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


def release_booking_payment(booking_id: int):
    """
    Rilascia il pagamento trattenuto al consulente dopo 48h dalla fine della consulenza.
    Verifica che non ci siano contestazioni aperte prima di trasferire.
    """
    try:
        with Session(engine) as session:
            booking = session.get(Booking, booking_id)
            if not booking:
                logger.error(f"❌ Booking {booking_id} non trovato per rilascio pagamento")
                return
            
            # Se il pagamento non è più in stato held, skip
            if booking.payment_status != "held":
                logger.info(f"⏭️ Booking {booking_id}: payment_status={booking.payment_status}, skip rilascio")
                return
            
            # Verifica contestazioni aperte
            open_disputes = session.exec(
                select(Dispute).where(
                    Dispute.booking_id == booking_id,
                    Dispute.status.in_(["open", "in_review"])
                )
            ).all()
            
            if open_disputes:
                logger.info(f"⚠️ Booking {booking_id}: contestazione aperta, rilascio bloccato")
                send_notification(
                    user_id=booking.consultant_user_id,
                    type_key="payment_hold",
                    title="Pagamento in attesa",
                    message=f"Il pagamento per la consulenza #{booking_id} è in attesa per una contestazione in corso."
                )
                return
            
            # Recupera consulente
            consultant = session.get(User, booking.consultant_user_id)
            
            # Calcola importo da trasferire (totale - fee piattaforma)
            amount_cents = int(float(booking.price) * 100)
            fee_percent = consultant.platform_fee_percent if consultant.platform_fee_percent else 20
            transfer_amount = amount_cents - int(amount_cents * fee_percent / 100)
            
            if booking.payment_method == "paypal":
                # === PayPal Payout ===
                if not consultant or not consultant.paypal_email:
                    logger.error(f"❌ Booking {booking_id}: consulente senza email PayPal, impossibile trasferire")
                    booking.payment_status = "paid"
                    session.add(booking)
                    session.commit()
                    return
                
                try:
                    from app.utils.paypal_config import create_payout
                    payout = create_payout(
                        recipient_email=consultant.paypal_email,
                        amount=round(transfer_amount / 100, 2),
                        currency="EUR",
                        note=f"Pagamento consulenza #{booking_id}",
                        sender_item_id=f"booking_{booking_id}"
                    )
                    
                    if payout:
                        payout_id = payout.get("batch_header", {}).get("payout_batch_id", "")
                        booking.paypal_payout_id = payout_id
                        booking.payment_status = "released"
                        booking.payment_released_at = datetime.now(ITALY_TZ)
                        session.add(booking)
                        session.commit()
                        
                        logger.info(f"✅ Booking {booking_id}: PayPal payout {payout_id}, €{transfer_amount/100:.2f} → {consultant.paypal_email}")
                        
                        send_notification(
                            user_id=booking.consultant_user_id,
                            type_key="payment_released",
                            title="Pagamento ricevuto!",
                            message=f"Il pagamento di €{transfer_amount/100:.2f} per la consulenza #{booking_id} è stato trasferito al tuo conto PayPal."
                        )
                    else:
                        logger.error(f"❌ Booking {booking_id}: PayPal payout fallito")
                        
                except Exception as e:
                    logger.error(f"❌ Booking {booking_id}: errore PayPal Payout: {e}")
            else:
                # === Stripe Transfer ===
                if not consultant or not consultant.stripe_account_id:
                    logger.error(f"❌ Booking {booking_id}: consulente senza account Stripe, impossibile trasferire")
                    booking.payment_status = "paid"
                    session.add(booking)
                    session.commit()
                    return
                
                try:
                    import stripe
                    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
                    transfer = stripe.Transfer.create(
                        amount=transfer_amount,
                        currency="eur",
                        destination=consultant.stripe_account_id,
                        transfer_group=f"booking_{booking_id}",
                        metadata={
                            "booking_id": str(booking_id),
                            "consultant_user_id": str(consultant.id),
                        }
                    )
                    
                    booking.stripe_transfer_id = transfer.id
                    booking.payment_status = "released"
                    booking.payment_released_at = datetime.now(ITALY_TZ)
                    session.add(booking)
                    session.commit()
                    
                    logger.info(f"✅ Booking {booking_id}: pagamento rilasciato, transfer {transfer.id}, €{transfer_amount/100:.2f} → {consultant.stripe_account_id}")
                    
                    send_notification(
                        user_id=booking.consultant_user_id,
                        type_key="payment_released",
                        title="Pagamento ricevuto!",
                        message=f"Il pagamento di €{transfer_amount/100:.2f} per la consulenza #{booking_id} è stato trasferito al tuo conto."
                    )
                    
                except Exception as e:
                    logger.error(f"❌ Booking {booking_id}: errore Stripe Transfer: {e}")
                
    except Exception as e:
        logger.error(f"❌ Errore rilascio pagamento booking {booking_id}: {e}")


def schedule_payment_release(booking_id: int, consultation_end_datetime: datetime):
    """
    Schedula il rilascio del pagamento 48h dopo la fine della consulenza.
    """
    try:
        if consultation_end_datetime.tzinfo is None:
            consultation_end_datetime = consultation_end_datetime.replace(tzinfo=ITALY_TZ)
        
        release_time = consultation_end_datetime + timedelta(hours=48)
        
        scheduler.add_job(
            release_booking_payment,
            trigger=DateTrigger(run_date=release_time),
            args=[booking_id],
            id=f"payment_release_{booking_id}",
            replace_existing=True,
            misfire_grace_time=3600  # 1 ora di tolleranza
        )
        logger.info(f"💰 Schedulato rilascio pagamento booking {booking_id} per {release_time}")
    except Exception as e:
        logger.error(f"❌ Errore scheduling rilascio pagamento: {e}")


def cancel_payment_release(booking_id: int):
    """
    Cancella il job schedulato di rilascio pagamento per un booking.
    Usato quando il booking viene cancellato/rifiutato.
    """
    try:
        job_id = f"payment_release_{booking_id}"
        scheduler.remove_job(job_id)
        logger.info(f"🗑️ Cancellato rilascio pagamento schedulato per booking {booking_id}")
    except JobLookupError:
        logger.info(f"ℹ️ Nessun job di rilascio pagamento da cancellare per booking {booking_id}")
    except Exception as e:
        logger.error(f"❌ Errore cancellazione rilascio pagamento: {e}")


def check_booking_noshow(booking_id: int):
    """
    Controlla la partecipazione alla consulenza dopo la fine della finestra temporale.
    - Consulente non si presenta → rimborso automatico al cliente
    - Cliente non si presenta → il consulente incassa normalmente
    - Entrambi presenti → booking completato
    """
    try:
        with Session(engine) as session:
            booking = session.get(Booking, booking_id)
            if not booking:
                logger.error(f"❌ Booking {booking_id} non trovato per check no-show")
                return
            
            # Solo booking confermati e non già gestiti
            if booking.status not in ("confirmed",):
                logger.info(f"⏭️ Booking {booking_id}: status={booking.status}, skip check no-show")
                return
            
            consultant_joined = booking.consultant_joined_at is not None
            client_joined = booking.client_joined_at is not None
            
            if consultant_joined and client_joined:
                # Entrambi presenti → consulenza completata
                booking.status = "completed"
                session.add(booking)
                session.commit()
                logger.info(f"✅ Booking {booking_id}: consulenza completata (entrambi presenti)")
                
            elif not consultant_joined and client_joined:
                # Consulente assente → rimborso automatico al cliente
                booking.status = "no_show"
                logger.info(f"⚠️ Booking {booking_id}: consulente non si è presentato, rimborso automatico")
                
                if booking.payment_status == "held":
                    if booking.payment_method == "paypal" and booking.paypal_capture_id:
                        try:
                            from app.utils.paypal_config import refund_capture
                            result = refund_capture(booking.paypal_capture_id)
                            if result:
                                booking.payment_status = "refunded"
                                logger.info(f"💸 Rimborso PayPal automatico per no-show consulente, booking {booking_id}")
                            else:
                                logger.error(f"❌ Errore rimborso PayPal no-show booking {booking_id}")
                        except Exception as e:
                            logger.error(f"❌ Errore rimborso PayPal no-show booking {booking_id}: {e}")
                    elif booking.stripe_payment_intent_id:
                        try:
                            import stripe
                            stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
                            refund = stripe.Refund.create(
                                payment_intent=booking.stripe_payment_intent_id,
                                reason='requested_by_customer'
                            )
                            booking.payment_status = "refunded"
                            logger.info(f"💸 Rimborso automatico {refund.id} per no-show consulente, booking {booking_id}")
                        except Exception as e:
                            logger.error(f"❌ Errore rimborso no-show booking {booking_id}: {e}")
                
                # Cancella il rilascio pagamento schedulato
                cancel_payment_release(booking_id)
                
                session.add(booking)
                session.commit()
                
                # Notifica al cliente
                send_notification(
                    user_id=booking.client_user_id,
                    type_key="booking_noshow",
                    title="Consulente assente",
                    message=f"Il consulente non si è presentato alla consulenza #{booking_id}. Il rimborso è stato effettuato automaticamente."
                )
                # Notifica al consulente
                send_notification(
                    user_id=booking.consultant_user_id,
                    type_key="booking_noshow",
                    title="Consulenza persa",
                    message=f"Non ti sei presentato alla consulenza #{booking_id}. Il cliente è stato rimborsato automaticamente."
                )
                
            elif not client_joined and consultant_joined:
                # Cliente assente → consulente incassa normalmente
                booking.status = "no_show"
                session.add(booking)
                session.commit()
                logger.info(f"⚠️ Booking {booking_id}: cliente non si è presentato, pagamento procede normalmente")
                
                send_notification(
                    user_id=booking.consultant_user_id,
                    type_key="booking_noshow",
                    title="Cliente assente",
                    message=f"Il cliente non si è presentato alla consulenza #{booking_id}. Il pagamento procede regolarmente."
                )
                
            else:
                # Nessuno si è presentato → rimborso al cliente
                booking.status = "no_show"
                logger.info(f"⚠️ Booking {booking_id}: nessuno si è presentato, rimborso al cliente")
                
                if booking.payment_status == "held":
                    if booking.payment_method == "paypal" and booking.paypal_capture_id:
                        try:
                            from app.utils.paypal_config import refund_capture
                            result = refund_capture(booking.paypal_capture_id)
                            if result:
                                booking.payment_status = "refunded"
                                logger.info(f"💸 Rimborso PayPal automatico (nessuno presente), booking {booking_id}")
                            else:
                                logger.error(f"❌ Errore rimborso PayPal no-show booking {booking_id}")
                        except Exception as e:
                            logger.error(f"❌ Errore rimborso PayPal no-show booking {booking_id}: {e}")
                    elif booking.stripe_payment_intent_id:
                        try:
                            import stripe
                            stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
                            refund = stripe.Refund.create(
                                payment_intent=booking.stripe_payment_intent_id,
                                reason='requested_by_customer'
                            )
                            booking.payment_status = "refunded"
                            logger.info(f"💸 Rimborso automatico {refund.id} (nessuno presente), booking {booking_id}")
                        except Exception as e:
                            logger.error(f"❌ Errore rimborso no-show booking {booking_id}: {e}")
                
                cancel_payment_release(booking_id)
                
                session.add(booking)
                session.commit()
                
                send_notification(
                    user_id=booking.client_user_id,
                    type_key="booking_noshow",
                    title="Consulenza non avvenuta",
                    message=f"La consulenza #{booking_id} non si è svolta. Il rimborso è stato effettuato automaticamente."
                )
                
    except Exception as e:
        logger.error(f"❌ Errore check no-show booking {booking_id}: {e}")


def schedule_noshow_check(booking_id: int, consultation_end_datetime: datetime):
    """
    Schedula il controllo no-show 15 minuti dopo la fine della consulenza.
    """
    try:
        if consultation_end_datetime.tzinfo is None:
            consultation_end_datetime = consultation_end_datetime.replace(tzinfo=ITALY_TZ)
        
        check_time = consultation_end_datetime + timedelta(minutes=15)
        
        scheduler.add_job(
            check_booking_noshow,
            trigger=DateTrigger(run_date=check_time),
            args=[booking_id],
            id=f"noshow_check_{booking_id}",
            replace_existing=True,
            misfire_grace_time=3600
        )
        logger.info(f"👀 Schedulato check no-show booking {booking_id} per {check_time}")
    except Exception as e:
        logger.error(f"❌ Errore scheduling check no-show: {e}")


def start_scheduler():
    """
    Avvia lo scheduler.
    Chiamata all'avvio dell'applicazione (in main.py).
    """
    if not scheduler.running:
        scheduler.start()
        logger.info("🚀 APScheduler avviato con successo")
    
    # Recovery: processa booking rimasti bloccati durante il downtime
    recover_stuck_bookings()


def recover_stuck_bookings():
    """
    Trova e processa booking rimasti con payment_status='held' che avrebbero
    dovuto essere gestiti (no-show check o rilascio pagamento) mentre il server
    era offline. Eseguita ad ogni startup.
    """
    try:
        now = datetime.now(ITALY_TZ)
        
        with Session(engine) as session:
            held_bookings = session.exec(
                select(Booking).where(Booking.payment_status == "held")
            ).all()
            
            if not held_bookings:
                logger.info("✅ Recovery: nessun booking bloccato trovato")
                return
            
            logger.info(f"🔍 Recovery: trovati {len(held_bookings)} booking con payment_status='held'")
            
            for booking in held_bookings:
                try:
                    if not booking.booking_date or not booking.end_time:
                        continue
                    
                    # Parse end_time (può essere str o time)
                    end_time = booking.end_time
                    if isinstance(end_time, str):
                        parts = end_time.split(":")
                        from datetime import time as dt_time
                        end_time = dt_time(int(parts[0]), int(parts[1]))
                    
                    end_dt = datetime.combine(booking.booking_date, end_time).replace(tzinfo=ITALY_TZ)
                    noshow_due = end_dt + timedelta(minutes=15)
                    release_due = end_dt + timedelta(hours=48)
                    
                    if now < noshow_due:
                        # Consulenza non ancora finita o nel grace period, rischedula normalmente
                        logger.info(f"⏳ Recovery booking {booking.id}: consulenza non ancora finita, rischedulo")
                        schedule_noshow_check(booking.id, end_dt)
                        schedule_payment_release(booking.id, end_dt)
                        
                    elif now >= noshow_due and booking.status == "confirmed":
                        # No-show check non eseguito, eseguilo ora
                        logger.info(f"🔄 Recovery booking {booking.id}: eseguo check no-show mancato")
                        check_booking_noshow(booking.id)
                        # Se dopo il no-show check è ancora held (es. client no-show), schedula il rilascio
                        session.refresh(booking)
                        if booking.payment_status == "held" and now >= release_due:
                            release_booking_payment(booking.id)
                        elif booking.payment_status == "held":
                            schedule_payment_release(booking.id, end_dt)
                            
                    elif now >= release_due:
                        # Rilascio pagamento scaduto, eseguilo ora
                        logger.info(f"🔄 Recovery booking {booking.id}: eseguo rilascio pagamento mancato")
                        release_booking_payment(booking.id)
                        
                    elif now >= noshow_due:
                        # Tra no-show e release, rischedula solo il rilascio
                        schedule_payment_release(booking.id, end_dt)
                    
                except Exception as e:
                    logger.error(f"❌ Recovery booking {booking.id}: errore: {e}")
            
            logger.info("✅ Recovery completata")
    
    except Exception as e:
        logger.error(f"❌ Errore recovery booking bloccati: {e}")


def shutdown_scheduler():
    """
    Ferma lo scheduler in modo pulito.
    Chiamata alla chiusura dell'applicazione.
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 APScheduler fermato")
