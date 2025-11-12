"""
Stripe Webhook Handler
Receives and processes Stripe events (payment confirmations, etc.)
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session
from datetime import datetime
from zoneinfo import ZoneInfo
import os
from app.database import engine
from app.models import Booking, ConsultationOffer, User, Notification
from app.utils.stripe_config import construct_webhook_event
from app.logger_config import logger
from app.scheduler import schedule_booking_reminders
from app.utils.notification_service import send_notification

router = APIRouter()

# Timezone italiano
ITALY_TZ = ZoneInfo("Europe/Rome")

@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events
    Stripe will call this endpoint when payment events occur
    """
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")
    
    try:
        # Verify webhook signature and construct event
        event = construct_webhook_event(payload, sig_header)
    except ValueError as e:
        logger.error(f"Invalid Stripe webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        await handle_checkout_session_completed(session)
    
    elif event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        logger.info(f"Payment intent succeeded: {payment_intent['id']}")
    
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        logger.warning(f"Payment intent failed: {payment_intent['id']}")
    
    # Return 200 to acknowledge receipt of the event
    return JSONResponse({"status": "success"})


async def handle_checkout_session_completed(checkout_session):
    """
    Handle successful payment - create booking in database
    """
    session_id = checkout_session['id']
    payment_intent_id = checkout_session.get('payment_intent')
    metadata = checkout_session['metadata']
    
    logger.info(f"Processing checkout session: {session_id}")
    
    # Check booking type
    booking_type = metadata.get('booking_type', 'consultation_offer')
    
    if booking_type == 'direct':
        # Direct booking (from booking.html)
        await handle_direct_booking(session_id, payment_intent_id, metadata)
    else:
        # Consultation offer booking (from consultation offer)
        await handle_consultation_offer_booking(session_id, payment_intent_id, metadata)


async def handle_direct_booking(session_id, payment_intent_id, metadata):
    """Handle direct booking payment"""
    client_user_id = int(metadata.get('client_user_id'))
    consultant_user_id = int(metadata.get('consultant_user_id'))
    booking_date_str = metadata.get('booking_date')
    start_time = metadata.get('start_time')
    end_time = metadata.get('end_time')
    duration_minutes = int(metadata.get('duration_minutes'))
    availability_block_id = metadata.get('availability_block_id')
    client_notes = metadata.get('client_notes', '')
    
    with Session(engine) as db_session:
        # Check if booking already exists
        existing_booking = db_session.query(Booking).filter(
            Booking.stripe_checkout_session_id == session_id
        ).first()
        
        if existing_booking:
            logger.info(f"Booking already exists for session {session_id}")
            return
        
        # Get consultant to get price
        consultant = db_session.get(User, consultant_user_id)
        if not consultant:
            logger.error(f"Consultant {consultant_user_id} not found")
            return
        
        price = consultant.prezzo_consulenza if consultant.prezzo_consulenza else 0
        
        # Parse booking datetime
        booking_datetime = datetime.strptime(f"{booking_date_str} {start_time}", "%Y-%m-%d %H:%M")
        
        # Create booking
        new_booking = Booking(
            client_user_id=client_user_id,
            consultant_user_id=consultant_user_id,
            availability_block_id=int(availability_block_id) if availability_block_id else None,
            booking_date=booking_datetime,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            price=price,
            status="confirmed",
            payment_status="paid",
            payment_method="stripe",
            stripe_checkout_session_id=session_id,
            stripe_payment_intent_id=payment_intent_id,
            client_notes=client_notes or f"Prenotazione diretta"
        )
        
        db_session.add(new_booking)
        db_session.commit()
        db_session.refresh(new_booking)
        
        # Get client and consultant info
        client = db_session.get(User, client_user_id)
        consultant = db_session.get(User, consultant_user_id)
        client_name = f"{client.nome} {client.cognome}" if client and client.nome else "Un utente"
        consultant_name = f"{consultant.nome} {consultant.cognome}" if consultant and consultant.nome else "Il consulente"
        
        # Invia notifica al consulente usando il nuovo sistema
        send_notification(
            user_id=consultant_user_id,
            type_key='booking_confirmed',
            title="Nuova Prenotazione!",
            message=f"{client_name} ha prenotato una consulenza per il {booking_date_str} alle {start_time}",
            template_data={
                'consultant_name': consultant_name,
                'client_name': client_name,
                'date': booking_date_str,
                'time': start_time,
                'duration': str(duration_minutes),
                'action_url': f"{os.getenv('BASE_URL', 'http://localhost:8080')}/profile#bookings"
            },
            related_booking_id=new_booking.id,
            related_user_id=client_user_id,
            action_url=f"/profile#bookings"
        )
        
        logger.info(f"✅ Direct booking {new_booking.id} created successfully for session {session_id}")
        
        # Schedula notifiche promemoria (1 ora prima e 10 minuti prima)
        booking_datetime_tz = booking_datetime.replace(tzinfo=ITALY_TZ)
        schedule_booking_reminders(
            booking_id=new_booking.id,
            booking_datetime=booking_datetime_tz,
            client_id=client_user_id,
            consultant_id=consultant_user_id
        )
        logger.info(f"📅 Notifiche reminder schedulate per booking {new_booking.id}")



async def handle_consultation_offer_booking(session_id, payment_intent_id, metadata):
    """Handle consultation offer booking payment"""
    offer_id = int(metadata.get('offer_id'))
    client_user_id = int(metadata.get('client_user_id'))
    consultant_user_id = int(metadata.get('consultant_user_id'))
    selected_date = metadata.get('selected_date')
    start_time = metadata.get('start_time')
    end_time = metadata.get('end_time')
    duration_minutes = int(metadata.get('duration_minutes'))
    
    with Session(engine) as db_session:
        # Get consultation offer
        offer = db_session.get(ConsultationOffer, offer_id)
        if not offer:
            logger.error(f"Consultation offer {offer_id} not found")
            return
        
        # Check if booking already exists for this session
        existing_booking = db_session.query(Booking).filter(
            Booking.stripe_checkout_session_id == session_id
        ).first()
        
        if existing_booking:
            logger.info(f"Booking already exists for session {session_id}")
            return
        
        # Parse booking datetime
        booking_datetime = datetime.strptime(f"{selected_date} {start_time}", "%Y-%m-%d %H:%M")
        
        # Create booking
        new_booking = Booking(
            client_user_id=client_user_id,
            consultant_user_id=consultant_user_id,
            booking_date=booking_datetime,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            price=offer.price,
            status="confirmed",
            payment_status="paid",
            payment_method="stripe",
            stripe_checkout_session_id=session_id,
            stripe_payment_intent_id=payment_intent_id,
            client_notes=f"Prenotazione da offerta consulenza #{offer.id}"
        )
        
        db_session.add(new_booking)
        db_session.commit()
        db_session.refresh(new_booking)
        
        # Update offer status
        offer.status = "accepted"
        offer.booking_id = new_booking.id
        offer.updated_at = datetime.utcnow()
        db_session.add(offer)
        db_session.commit()
        
        # Get client and consultant info
        client = db_session.get(User, client_user_id)
        consultant = db_session.get(User, consultant_user_id)
        client_name = f"{client.nome} {client.cognome}" if client and client.nome else "Un utente"
        consultant_name = f"{consultant.nome} {consultant.cognome}" if consultant and consultant.nome else "Il consulente"
        
        # Invia notifica al consulente usando il nuovo sistema
        send_notification(
            user_id=consultant_user_id,
            type_key='booking_confirmed',
            title="Nuova Prenotazione!",
            message=f"{client_name} ha accettato la tua offerta e prenotato per il {selected_date} alle {start_time}",
            template_data={
                'consultant_name': consultant_name,
                'client_name': client_name,
                'date': selected_date,
                'time': start_time,
                'duration': str(duration_minutes),
                'action_url': f"{os.getenv('BASE_URL', 'http://localhost:8080')}/profile#bookings"
            },
            related_booking_id=new_booking.id,
            related_user_id=client_user_id,
            action_url=f"/profile#bookings"
        )
        
        logger.info(f"✅ Booking {new_booking.id} created successfully for session {session_id}")
        
        # Schedula notifiche promemoria (1 ora prima e 10 minuti prima)
        booking_datetime_tz = booking_datetime.replace(tzinfo=ITALY_TZ)
        schedule_booking_reminders(
            booking_id=new_booking.id,
            booking_datetime=booking_datetime_tz,
            client_id=client_user_id,
            consultant_id=consultant_user_id
        )
        logger.info(f"📅 Notifiche reminder schedulate per booking {new_booking.id}")

