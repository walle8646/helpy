from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func
from datetime import datetime, timedelta, time
from typing import Optional, List, Dict, Union
from zoneinfo import ZoneInfo
from pydantic import BaseModel
import os
import asyncio
from app.database import engine
from app.models import Booking, User, AvailabilityBlock, CallMessage
from app.routes.auth import get_current_user
from app.utils.agora_recording import start_recording, stop_recording, get_recording_url
from app.logger_config import logger
from app.utils.stripe_config import create_checkout_session
from app.utils.notification_service import send_notification

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# ===== PYDANTIC MODELS =====
class ChatMessageRequest(BaseModel):
    message: str

# Timezone italiano
ITALY_TZ = ZoneInfo("Europe/Rome")

# Lock per sincronizzare join_booking per lo stesso booking
# Evita race condition quando il client chiama join multiple volte
_booking_locks: Dict[int, asyncio.Lock] = {}

def get_booking_lock(booking_id: int) -> asyncio.Lock:
    """Ottiene un lock univoco per il booking"""
    if booking_id not in _booking_locks:
        _booking_locks[booking_id] = asyncio.Lock()
    return _booking_locks[booking_id]

def parse_time_to_minutes(time_input: Union[str, time]) -> int:
    """Converte una stringa HH:MM o un oggetto time in minuti dalla mezzanotte"""
    if isinstance(time_input, time):
        # Se è già un oggetto time, usa hour e minute
        return time_input.hour * 60 + time_input.minute
    # Se è una stringa, fai il parsing
    hours, minutes = map(int, time_input.split(':'))
    return hours * 60 + minutes

def minutes_to_time(minutes: int) -> str:
    """Converte minuti dalla mezzanotte in stringa HH:MM"""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"

def calculate_available_slots(
    availability_blocks: List[AvailabilityBlock],
    existing_bookings: List[Booking],
    duration_minutes: int,
    date_str: str
) -> List[Dict]:
    """
    Calcola gli slot disponibili per una data e durata specificata.
    
    Args:
        availability_blocks: Blocchi di disponibilità del consulente
        existing_bookings: Prenotazioni già esistenti
        duration_minutes: Durata desiderata (30, 60, 90, 120)
        date_str: Data in formato "YYYY-MM-DD"
    
    Returns:
        Lista di slot disponibili con start_time e end_time
    """
    available_slots = []
    
    # Determina l'ora minima per la data odierna (timezone italiano)
    now_italy = datetime.now(ITALY_TZ)
    today = now_italy.date()
    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    # Calcola il minimo datetime: 4 ore nel futuro dal momento attuale
    min_datetime = now_italy + timedelta(hours=4)
    
    # Se il minimo datetime è dopo il target_date (cioè il target_date è nel passato rispetto al limite),
    # allora non ci sono slot disponibili per questa data
    if target_date < min_datetime.date():
        print(f"🕐 Data {target_date} è prima del limite di 4 ore ({min_datetime.date()}), nessuno slot disponibile")
        return []
    
    # Calcola i minuti da inizio giornata per il minimo time
    if min_datetime.date() == target_date:
        # Il limite di 4 ore cade nello stesso giorno della prenotazione
        current_time_minutes = min_datetime.hour * 60 + min_datetime.minute
    else:
        # Il limite di 4 ore cade in un giorno precedente (target_date è dopo il limite)
        # Quindi nessun limite per questo giorno (può iniziare da 00:00)
        current_time_minutes = 0
    
    print(f"🕐 calculate_available_slots: now={now_italy}, min_datetime={min_datetime}, target_date={target_date}, current_time_minutes={current_time_minutes}")
    
    for block in availability_blocks:
        # Converti start_time e end_time in minuti
        block_start = parse_time_to_minutes(block.start_time)
        block_end = parse_time_to_minutes(block.end_time)
        
        # Calcola il minimo di tempo richiesto (4 ore dal momento attuale)
        min_start_time = current_time_minutes if current_time_minutes is not None else 0
        
        if block_end <= min_start_time:
            # Tutto il blocco è nel passato o entro il limite di 4 ore, saltalo
            continue
        # Aggiorna il block_start se parte del blocco è nel passato/entro 4 ore
        if block_start < min_start_time:
            # Arrotonda al prossimo slot di 30 minuti
            block_start = ((min_start_time + 29) // 30) * 30
        
        # Crea lista di intervalli occupati in questo blocco
        occupied_intervals = []
        for booking in existing_bookings:
            if booking.availability_block_id == block.id or (
                booking.booking_date.strftime('%Y-%m-%d') == date_str and
                booking.status not in ['cancelled', 'no_show']
            ):
                booking_start = parse_time_to_minutes(booking.start_time)
                booking_end = parse_time_to_minutes(booking.end_time)
                occupied_intervals.append((booking_start, booking_end))
        
        # Ordina gli intervalli occupati
        occupied_intervals.sort()
        
        # Calcola slot disponibili
        current_time = block_start
        
        for occupied_start, occupied_end in occupied_intervals:
            # C'è spazio prima di questo intervallo occupato?
            while current_time + duration_minutes <= occupied_start:
                slot = {
                    'start_time': minutes_to_time(current_time),
                    'end_time': minutes_to_time(current_time + duration_minutes),
                    'availability_block_id': block.id
                }
                available_slots.append(slot)
                print(f"   ✅ Slot aggiunto: {slot['start_time']} - {slot['end_time']}")
                current_time += 15  # Incremento di 15 minuti per slot successivo
            
            # Salta l'intervallo occupato
            current_time = max(current_time, occupied_end)
        
        # Slot disponibili dopo l'ultimo intervallo occupato
        while current_time + duration_minutes <= block_end:
            slot = {
                'start_time': minutes_to_time(current_time),
                'end_time': minutes_to_time(current_time + duration_minutes),
                'availability_block_id': block.id
            }
            available_slots.append(slot)
            print(f"   ✅ Slot aggiunto (dopo): {slot['start_time']} - {slot['end_time']}")
            current_time += 15
    
    return available_slots

# ========== PAGINA PRENOTAZIONE ==========

@router.get("/book/{consultant_id}", response_class=HTMLResponse, name="booking_page")
async def booking_page(
    request: Request,
    consultant_id: int
):
    """Pagina di prenotazione con il consulente"""
    # Verifica che l'utente sia autenticato
    current_user = get_current_user(request)
    if not current_user:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Devi effettuare il login per prenotare una consulenza"
        })
    
    with Session(engine) as session:
        # Prendi i dati del consulente
        consultant = session.get(User, consultant_id)
        if not consultant:
            raise HTTPException(status_code=404, detail="Consulente non trovato")
        
        # Non puoi prenotare con te stesso
        if current_user.id == consultant_id:
            raise HTTPException(status_code=400, detail="Non puoi prenotare una consulenza con te stesso")
        
        return templates.TemplateResponse("booking.html", {
            "request": request,
            "user": current_user,
            "current_user": current_user,  # Per la navbar
            "consultant": consultant
        })

# ========== API ENDPOINTS ==========

@router.get("/api/booking/available-slots/{consultant_id}")
async def get_available_slots(
    consultant_id: int,
    date: str,
    duration: int
):
    """
    Restituisce gli slot disponibili per un consulente in una data specifica.
    
    Args:
        consultant_id: ID del consulente
        date: Data in formato YYYY-MM-DD
        duration: Durata in minuti (30, 60, 90, 120)
    """
    # Validazione durata
    if duration not in [30, 60, 90, 120]:
        raise HTTPException(status_code=400, detail="Durata non valida. Valori ammessi: 30, 60, 90, 120")
    
    with Session(engine) as session:
        # Verifica che il consulente esista
        consultant = session.get(User, consultant_id)
        if not consultant:
            raise HTTPException(status_code=404, detail="Consulente non trovato")
        
        # Parse della data
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato data non valido. Usa YYYY-MM-DD")
        
        # Non si può prenotare nel passato (usa timezone italiano)
        today_italy = datetime.now(ITALY_TZ).date()
        if target_date < today_italy:
            raise HTTPException(status_code=400, detail="Non puoi prenotare nel passato")
        
        # Prendi i blocchi di disponibilità per quella data
        availability_blocks = session.exec(
            select(AvailabilityBlock)
            .where(func.date(AvailabilityBlock.date) == date)
            .where(AvailabilityBlock.user_id == consultant_id)
            .where(AvailabilityBlock.is_active == True)
            .where(AvailabilityBlock.status == "available")
        ).all()
        
        # DEBUG: Log dei blocchi trovati
        print(f"🔍 DEBUG - Date: {date}, Consultant: {consultant_id}")
        print(f"📅 Blocchi trovati: {len(availability_blocks)}")
        for block in availability_blocks:
            print(f"   Block ID {block.id}: {block.start_time} - {block.end_time} (status: {block.status}, active: {block.is_active})")
        
        if not availability_blocks:
            return {"slots": [], "message": "Il consulente non è disponibile in questa data"}
        
        # Prendi le prenotazioni esistenti per quella data
        existing_bookings = session.exec(
            select(Booking)
            .where(func.date(Booking.booking_date) == date)
            .where(Booking.consultant_user_id == consultant_id)
            .where(Booking.status.in_(['pending', 'confirmed']))
        ).all()
        
        # Calcola gli slot disponibili
        available_slots = calculate_available_slots(
            availability_blocks,
            existing_bookings,
            duration,
            date
        )
        
        return {
            "slots": available_slots,
            "consultant": {
                "id": consultant.id,
                "nome": consultant.nome,
                "cognome": consultant.cognome,
                "prezzo": consultant.prezzo_consulenza
            },
            "date": date,
            "duration_minutes": duration
        }

@router.post("/api/booking/create")
async def create_booking(
    request: Request,
    booking_data: dict
):
    """
    Crea Stripe Checkout Session per prenotazione.
    
    Body:
        consultant_user_id: int
        booking_date: str (YYYY-MM-DD)
        start_time: str (HH:MM)
        end_time: str (HH:MM)
        duration_minutes: int
        availability_block_id: int (optional)
        client_notes: str (optional)
    """
    import os
    
    # Verifica autenticazione
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    # Validazione dati
    consultant_id = booking_data.get('consultant_user_id')
    booking_date_str = booking_data.get('booking_date')
    start_time = booking_data.get('start_time')
    end_time = booking_data.get('end_time')
    duration_minutes = booking_data.get('duration_minutes')
    availability_block_id = booking_data.get('availability_block_id')
    client_notes = booking_data.get('client_notes', '')
    price = booking_data.get('price')  # Prezzo calcolato dal frontend
    
    # Validazioni
    if not all([consultant_id, booking_date_str, start_time, end_time, duration_minutes, price]):
        raise HTTPException(status_code=400, detail="Campi obbligatori mancanti")
    
    if duration_minutes not in [30, 60, 90, 120]:
        raise HTTPException(status_code=400, detail="Durata non valida")
    
    # Non puoi prenotare con te stesso
    if current_user.id == consultant_id:
        raise HTTPException(status_code=400, detail="Non puoi prenotare con te stesso")
    
    with Session(engine) as session:
        # Verifica che il consulente esista
        consultant = session.get(User, consultant_id)
        if not consultant:
            raise HTTPException(status_code=404, detail="Consulente non trovato")
        
        # Parse della data
        try:
            booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato data non valido")
        
        # ✅ Validazione: prenotazione almeno 4 ore nel futuro
        # Combina data + ora di inizio
        booking_datetime = datetime.strptime(f"{booking_date_str} {start_time}", '%Y-%m-%d %H:%M')
        now = datetime.utcnow()
        time_until_booking = (booking_datetime - now).total_seconds() / 3600  # in ore
        
        if time_until_booking < 4:
            raise HTTPException(status_code=400, detail="La consulenza deve essere prenotata almeno 4 ore nel futuro")
        
        # Verifica che lo slot sia ancora disponibile (prevenzione double booking)
        existing_booking = session.exec(
            select(Booking)
            .where(func.date(Booking.booking_date) == booking_date_str)
            .where(Booking.consultant_user_id == consultant_id)
            .where(Booking.start_time == start_time)
            .where(Booking.status.in_(['pending', 'confirmed']))
        ).first()
        
        if existing_booking:
            raise HTTPException(status_code=409, detail="Questo slot è già stato prenotato")
        
        # Validazione prezzo ricevuto dal frontend
        if not price or price <= 0:
            raise HTTPException(status_code=400, detail="Prezzo non valido")
        
        # Verifica che il prezzo sia coerente con la tariffa del consulente
        hourly_rate = consultant.prezzo_consulenza if consultant.prezzo_consulenza else 0
        if hourly_rate <= 0:
            raise HTTPException(status_code=400, detail="Il consulente non ha impostato un prezzo")
        
        # Calcola il prezzo atteso basato sulla durata
        expected_price = (hourly_rate / 60) * duration_minutes
        # Tolleranza di 1 euro per arrotondamenti
        if abs(price - expected_price) > 1:
            raise HTTPException(status_code=400, detail="Prezzo non valido per la durata selezionata")
        
        # Get APP_URL from environment
        app_url = os.getenv("BASE_URL", "http://localhost:8080")
        
        # Create Stripe Checkout Session
        try:
            # Convert price to cents (Stripe uses smallest currency unit)
            amount_cents = int(float(price) * 100)
            
            checkout_session = create_checkout_session(
                amount=amount_cents,
                currency='eur',
                success_url=f"{app_url}/booking/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{app_url}/book/{consultant_id}?cancelled=true",
                metadata={
                    'booking_type': 'direct',  # differenzia da consultation offer
                    'client_user_id': str(current_user.id),
                    'consultant_user_id': str(consultant_id),
                    'booking_date': booking_date_str,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration_minutes': str(duration_minutes),
                    'availability_block_id': str(availability_block_id) if availability_block_id else '',
                    'client_notes': client_notes
                }
            )
            
            return {
                "success": True,
                "checkout_url": checkout_session.url,
                "session_id": checkout_session.id
            }
            
        except Exception as e:
            logger.error(f"Error creating Stripe checkout session: {e}")
            raise HTTPException(status_code=500, detail=f"Errore nella creazione del pagamento: {str(e)}")

@router.get("/api/booking/my-bookings")
async def get_my_bookings(
    request: Request
):
    """Restituisce tutte le prenotazioni dell'utente corrente (come cliente o consulente)"""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    with Session(engine) as session:
        # Prenotazioni come cliente (solo quelle pagate)
        bookings_as_client = session.exec(
            select(Booking)
            .where(Booking.client_user_id == current_user.id)
            .where(Booking.payment_status == 'paid')
            .order_by(Booking.booking_date.desc())
        ).all()
        
        # Prenotazioni come consulente (solo quelle pagate)
        bookings_as_consultant = session.exec(
            select(Booking)
            .where(Booking.consultant_user_id == current_user.id)
            .where(Booking.payment_status == 'paid')
            .order_by(Booking.booking_date.desc())
        ).all()
        
        # Formatta i risultati
        def format_booking(booking: Booking, role: str):
            other_user_id = booking.consultant_user_id if role == 'client' else booking.client_user_id
            other_user = session.get(User, other_user_id)
            
            return {
                "id": booking.id,
                "date": booking.booking_date.strftime('%Y-%m-%d'),
                "start_time": booking.start_time,
                "end_time": booking.end_time,
                "duration_minutes": booking.duration_minutes,
                "status": booking.status,
                "payment_status": booking.payment_status,
                "price": float(booking.price) if booking.price else 0,
                "role": role,
                "other_user": {
                    "id": other_user.id,
                    "nome": other_user.nome,
                    "cognome": other_user.cognome,
                    "profile_picture": other_user.profile_picture
                } if other_user else None,
                "meeting_link": booking.meeting_link,
                "notes": booking.client_notes if role == 'client' else booking.consultant_notes
            }
        
        return {
            "as_client": [format_booking(b, 'client') for b in bookings_as_client],
            "as_consultant": [format_booking(b, 'consultant') for b in bookings_as_consultant]
        }

@router.get("/api/booking/upcoming")
async def get_upcoming_bookings(request: Request):
    """Ottiene i prossimi 3 appuntamenti futuri dell'utente"""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    with Session(engine) as session:
        # Usa datetime.now() per l'ora locale
        now = datetime.now()
        
        # Query per prenotazioni confermate FUTURE (dopo adesso) e pagate
        statement = select(Booking).where(
            (Booking.client_user_id == current_user.id) | (Booking.consultant_user_id == current_user.id),
            Booking.status.in_(['confirmed', 'pending']),
            Booking.payment_status == 'paid'
        ).order_by(Booking.booking_date, Booking.start_time)
        
        bookings = session.exec(statement).all()
        
        upcoming = []
        for booking in bookings:
            # Calcola quando inizia l'appuntamento
            # booking.booking_date potrebbe essere date o datetime, convertiamo sempre a date
            if isinstance(booking.booking_date, str):
                booking_date = datetime.fromisoformat(booking.booking_date.split()[0]).date()
            elif isinstance(booking.booking_date, datetime):
                booking_date = booking.booking_date.date()
            else:
                booking_date = booking.booking_date
                
            booking_datetime = datetime.combine(
                booking_date,
                datetime.strptime(booking.start_time, "%H:%M").time()
            )
            
            # Calcola i minuti fino all'inizio
            time_until = (booking_datetime - now).total_seconds() / 60
            
            # FILTRO: Salta appuntamenti passati (prima di ora)
            if time_until < -booking.duration_minutes:
                continue
            
            print(f"DEBUG: booking_date={booking_date}, booking_datetime={booking_datetime}, now={now}, time_until={time_until}")
            
            # Determina il ruolo dell'utente corrente
            is_client = booking.client_user_id == current_user.id
            role = 'client' if is_client else 'consultant'
            
            # Ottieni i dati dell'altra persona
            other_user_id = booking.consultant_user_id if is_client else booking.client_user_id
            other_user = session.get(User, other_user_id)
            
            # Determina lo stato per l'UI
            can_join = time_until <= 10 and time_until >= -10  # Da 10 min prima a 10 min dopo inizio
            has_joined = booking.client_joined_at is not None if is_client else booking.consultant_joined_at is not None
            other_joined = booking.consultant_joined_at is not None if is_client else booking.client_joined_at is not None
            can_start_call = has_joined and other_joined
            
            upcoming.append({
                "id": booking.id,
                "date": str(booking_date) if not isinstance(booking.booking_date, str) else booking.booking_date,
                "start_time": booking.start_time,
                "end_time": booking.end_time,
                "duration": booking.duration_minutes,
                "status": booking.status,
                "payment_status": booking.payment_status,
                "stripe_payment_intent_id": booking.stripe_payment_intent_id,
                "role": role,
                "other_user": {
                    "name": f"{other_user.nome} {other_user.cognome}" if other_user else "Utente",
                    "profession": other_user.professione if other_user else "",
                    "picture": other_user.profile_picture if other_user else None
                },
                "time_until_minutes": int(time_until),
                "can_join": can_join,
                "has_joined": has_joined,
                "other_joined": other_joined,
                "can_start_call": can_start_call
            })
            
            # LIMITE: Mostra massimo 3 appuntamenti
            if len(upcoming) >= 3:
                break
        
        return {"bookings": upcoming}

@router.post("/api/booking/{booking_id}/join")
async def join_booking(booking_id: int, request: Request):
    """Segna che l'utente ha cliccato 'Partecipa' per un appuntamento"""
    # Acquisisci il lock per questo booking per evitare race condition
    lock = get_booking_lock(booking_id)
    async with lock:
        current_user = get_current_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Non autenticato")
    
    with Session(engine) as session:
        booking = session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Prenotazione non trovata")
        
        # Verifica che l'utente sia parte della prenotazione
        if current_user.id not in [booking.client_user_id, booking.consultant_user_id]:
            raise HTTPException(status_code=403, detail="Non autorizzato")
        
        # Determina il ruolo e salva il timestamp
        is_client = booking.client_user_id == current_user.id
        now = datetime.now()
        
        if is_client:
            if booking.client_joined_at is None:  # Solo se non ha già joinato
                booking.client_joined_at = now
        else:
            if booking.consultant_joined_at is None:  # Solo se non ha già joinato
                booking.consultant_joined_at = now
        
        booking.updated_at = now
        session.add(booking)
        session.commit()
        session.refresh(booking)
        
        # Controlla se entrambi hanno joinato
        client_joined = booking.client_joined_at is not None
        consultant_joined = booking.consultant_joined_at is not None
        
        logger.info(f"🔍 Join check for booking {booking_id}: client_joined={client_joined}, consultant_joined={consultant_joined}, recording_status={booking.recording_status}")

        if booking.recording_status == "failed" and (client_joined or consultant_joined):
            logger.warning(
                f"♻️ Previous recording attempt failed for booking {booking_id}; resetting state to allow retry"
            )
            booking.recording_status = "not_started"
            booking.recording_sid = None
            booking.recording_resource_id = None
            booking.recording_started_at = None
            booking.recording_filename = None
            booking.updated_at = now
            session.add(booking)
            session.commit()
            session.refresh(booking)
            logger.info(f"✅ Recording state reset for booking {booking_id}; new attempt permitted")
        
        # 🎥 NUOVO: Avvia registrazione automatica se almeno uno ha joinato
        # Se lo status è "completed" significa che gli utenti hanno riiniziato dopo aver chiuso
        # → riavvia una nuova registrazione con un nuovo session counter
        should_start_recording = (client_joined or consultant_joined) and booking.recording_status not in ("recording", "failed")
        
        # Se la registrazione era completata e qualcuno rejoin → incrementa session counter
        if booking.recording_status == "completed" and (client_joined or consultant_joined):
            logger.info(f"🔄 User rejoined after previous recording completed - starting new session")
            booking.recording_session_count = (booking.recording_session_count or 0) + 1
            booking.recording_status = None  # Reset status per far ripartire la registrazione
            session.add(booking)
            session.commit()
            session.refresh(booking)
        
        logger.info(f"🎥 Should start recording? {should_start_recording} (status={booking.recording_status})")
        
        if should_start_recording:
            try:
                logger.info(f"🎯 [join_booking] Attempting to prepare recording...")
                from app.utils.agora_token import generate_agora_token, ROLE_PUBLISHER
                
                recorder_uid = 0  # uid=0 per permettere a qualsiasi uid di registrare
                channel_name = f"booking_{booking_id}"
                
                logger.info(f"🔧 Generating token for recorder (uid={recorder_uid}, channel={channel_name})...")
                # Genera token per il recorder
                recorder_token = generate_agora_token(channel_name, recorder_uid, ROLE_PUBLISHER, 7200)
                logger.info(f"✓ Token generated successfully")
                
                # Salva token per quando il frontend è pronto
                booking.recording_status = "ready"
                booking.updated_at = now
                session.add(booking)
                session.commit()
                session.refresh(booking)
                
                logger.info(f"✅ Recording prepared for booking {booking_id} - waiting for frontend signal")
            except Exception as e:
                logger.error(f"❌ Error preparing recording for booking {booking_id}: {e}", exc_info=True)
                logger.error(f"❌ Exception type: {type(e).__name__}, Message: {str(e)}")
                # Continua anche se la registrazione fallisce
        else:
            if not (client_joined or consultant_joined):
                logger.info(f"ℹ️ Skipping recording start: neither client nor consultant have joined yet")
            elif booking.recording_status == "recording":
                logger.info(f"ℹ️ Skipping recording start: already recording")
            elif booking.recording_status == "failed":
                logger.info(f"ℹ️ Skipping recording start: previous recording failed")
        
        return {
            "success": True,
            "has_joined": True,
            "other_joined": consultant_joined if is_client else client_joined,
            "can_start_call": client_joined and consultant_joined,
            "recording_status": booking.recording_status
        }

@router.get("/api/booking/{booking_id}/agora-token")
async def get_agora_token(booking_id: int, request: Request):
    """Genera un token Agora per accedere alla video call"""
    from app.utils.agora_token import generate_booking_call_token
    
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    with Session(engine) as session:
        booking = session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Prenotazione non trovata")
        
        # Verifica che l'utente sia parte della prenotazione
        if current_user.id not in [booking.client_user_id, booking.consultant_user_id]:
            raise HTTPException(status_code=403, detail="Non autorizzato")
        
        # Verifica che entrambi abbiano joinato
        if not booking.client_joined_at or not booking.consultant_joined_at:
            raise HTTPException(status_code=403, detail="Entrambi i partecipanti devono aver cliccato 'Partecipa'")
        
        # Genera il token Agora
        try:
            token_data = generate_booking_call_token(booking_id, current_user.id)
            
            # Determina il ruolo dell'utente
            is_client = booking.client_user_id == current_user.id
            
            # Ottieni i dati dell'altro partecipante
            other_user_id = booking.consultant_user_id if is_client else booking.client_user_id
            other_user = session.get(User, other_user_id)
            
            return {
                "success": True,
                "token": token_data["token"],
                "app_id": token_data["app_id"],
                "channel_name": token_data["channel_name"],
                "uid": token_data["uid"],
                "expiration": token_data["expiration"],
                "booking": {
                    "id": booking.id,
                    "duration_minutes": booking.duration_minutes,
                    "start_time": booking.start_time,
                    "end_time": booking.end_time
                },
                "user_role": "client" if is_client else "consultant",
                "other_user": {
                    "name": f"{other_user.nome} {other_user.cognome}" if other_user else "Utente",
                    "profession": other_user.professione if other_user else ""
                }
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Errore generazione token: {str(e)}")

@router.get("/booking/call/{booking_id}")
async def call_page(booking_id: int, request: Request):
    """Pagina placeholder per la call"""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    with Session(engine) as session:
        booking = session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Prenotazione non trovata")
        
        if current_user.id not in [booking.client_user_id, booking.consultant_user_id]:
            raise HTTPException(status_code=403, detail="Non autorizzato")
        
        return templates.TemplateResponse("call.html", {
            "request": request,
            "user": current_user,
            "current_user": current_user,
            "booking": booking
        })

@router.delete("/api/booking/cancel/{booking_id}")
async def cancel_booking(
    booking_id: int,
    request: Request,
    reason: Optional[str] = None
):
    """Cancella una prenotazione"""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    with Session(engine) as session:
        booking = session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Prenotazione non trovata")
        
        # Solo il cliente o il consulente possono cancellare
        if current_user.id not in [booking.client_user_id, booking.consultant_user_id]:
            raise HTTPException(status_code=403, detail="Non autorizzato")
        
        # Non si può cancellare una prenotazione già completata
        if booking.status in ['completed', 'cancelled']:
            raise HTTPException(status_code=400, detail="Non puoi cancellare questa prenotazione")
        
        # Aggiorna lo stato
        booking.status = 'cancelled'
        booking.cancelled_by = current_user.id
        booking.cancelled_at = datetime.utcnow()
        booking.cancellation_reason = reason
        booking.updated_at = datetime.utcnow()
        
        session.add(booking)
        session.commit()
        
        return {
            "success": True,
            "message": "Prenotazione cancellata"
        }

# ========== CLOUD RECORDING ENDPOINTS ==========

@router.post("/api/booking/{booking_id}/recording/start")
async def start_booking_recording(booking_id: int, request: Request):
    """Avvia la registrazione cloud per una prenotazione"""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    with Session(engine) as session:
        booking = session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Prenotazione non trovata")
        
        # Solo client e consultant possono avviare recording
        if current_user.id not in [booking.client_user_id, booking.consultant_user_id]:
            raise HTTPException(status_code=403, detail="Non autorizzato")
        
        # Verifica che entrambi abbiano joinato
        if not booking.client_joined_at or not booking.consultant_joined_at:
            raise HTTPException(status_code=400, detail="Entrambi gli utenti devono essere presenti")
        
        # Non avviare se già in recording
        if booking.recording_status == "recording":
            raise HTTPException(status_code=400, detail="Recording già avviato")
        
        # Genera token per il bot recorder (UID speciale)
        from app.utils.agora_token import generate_agora_token, ROLE_PUBLISHER
        
        recorder_uid = 0  # UID fisso per il bot recorder
        channel_name = f"booking_{booking_id}"
        recorder_token = generate_agora_token(channel_name, recorder_uid, ROLE_PUBLISHER, 7200)
        
        # Avvia recording
        result = start_recording(channel_name, recorder_uid, recorder_token)
        
        if not result:
            raise HTTPException(status_code=500, detail="Errore avvio registrazione")
        
        # Aggiorna booking
        booking.recording_sid = result["sid"]
        booking.recording_resource_id = result["resource_id"]
        booking.recording_status = "recording"
        booking.recording_started_at = datetime.utcnow()
        booking.updated_at = datetime.utcnow()
        
        session.add(booking)
        session.commit()
        
        return {
            "success": True,
            "recording_sid": result["sid"],
            "message": "Registrazione avviata"
        }

@router.post("/api/booking/{booking_id}/recording/start-now")
async def start_recording_now(booking_id: int, request: Request):
    """Endpoint che il frontend chiama quando è pronto a registrare"""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    with Session(engine) as session:
        booking = session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Prenotazione non trovata")
        
        # Verifica che l'utente sia parte della prenotazione
        if current_user.id not in [booking.client_user_id, booking.consultant_user_id]:
            raise HTTPException(status_code=403, detail="Non autorizzato")
        
        # Se non è in uno stato di registrazione, non fare nulla
        if booking.recording_status != "ready":
            logger.info(f"⚠️ Recording not in 'ready' state for booking {booking_id} (current: {booking.recording_status})")
            return {"success": False, "message": f"Recording not ready (status={booking.recording_status})"}
        
        try:
            from app.utils.agora_recording import start_recording
            from app.utils.agora_token import generate_agora_token, ROLE_PUBLISHER
            
            recorder_uid = 0
            channel_name = f"booking_{booking_id}"
            
            logger.info(f"🎬 [start-now] Frontend is ready, starting recording for booking {booking_id}...")
            
            # Genera token per il recorder
            recorder_token = generate_agora_token(channel_name, recorder_uid, ROLE_PUBLISHER, 7200)
            
            # Avvia registrazione
            result = start_recording(channel_name, recorder_uid, recorder_token)
            
            if result:
                now = datetime.utcnow()
                timestamp_str = booking.created_at.strftime("%Y%m%d_%H%M%S")
                session_num = booking.recording_session_count or 1
                recording_name = f"booking_{booking_id}_{timestamp_str}_session{session_num}"
                
                logger.info(f"✅ Recording started successfully: {recording_name}")
                
                booking.recording_sid = result["sid"]
                booking.recording_resource_id = result["resource_id"]
                booking.recording_status = "recording"
                booking.recording_started_at = now
                booking.recording_filename = recording_name
                booking.updated_at = now
                
                session.add(booking)
                session.commit()
                session.refresh(booking)
                
                return {
                    "success": True,
                    "message": "Recording started",
                    "sid": result["sid"],
                    "filename": recording_name
                }
            else:
                logger.error(f"❌ Failed to start recording for booking {booking_id}")
                booking.recording_status = "failed"
                session.add(booking)
                session.commit()
                
                return {"success": False, "message": "Failed to start recording"}
        
        except Exception as e:
            logger.error(f"❌ Error in start_recording_now: {e}", exc_info=True)
            booking.recording_status = "failed"
            session.add(booking)
            session.commit()
            
            raise HTTPException(status_code=500, detail=f"Error starting recording: {str(e)}")

@router.post("/api/booking/{booking_id}/recording/stop")
async def stop_booking_recording(booking_id: int, request: Request):
    """Ferma la registrazione cloud"""
    current_user = get_current_user(request)
    if not current_user:
        # Se chiamato da sendBeacon, potrebbe non avere la sessione
        # Tentiamo comunque di fermare la registrazione
        with Session(engine) as session:
            booking = session.get(Booking, booking_id)
            if booking and booking.recording_status == "recording":
                # Ferma senza autenticazione (emergenza)
                recorder_uid = 0
                channel_name = f"booking_{booking_id}"
                
                try:
                    result = stop_recording(
                        booking.recording_resource_id,
                        booking.recording_sid,
                        channel_name,
                        recorder_uid
                    )
                    
                    if result:
                        file_name = result["file_name"]
                        recording_url = get_recording_url(file_name)
                        booking.recording_url = recording_url
                        booking.recording_duration = result.get("mix_duration", 0)
                        booking.recording_status = "completed"
                    else:
                        booking.recording_status = "failed"
                    
                    booking.recording_completed_at = datetime.utcnow()
                    booking.updated_at = datetime.utcnow()
                    session.add(booking)
                    session.commit()
                except Exception as e:
                    print(f"Errore stop recording (no auth): {e}")
                    pass
        
        return {"success": True, "message": "Recording stop tentato"}
    
    with Session(engine) as session:
        booking = session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Prenotazione non trovata")
        
        # Solo client e consultant possono fermare recording
        if current_user.id not in [booking.client_user_id, booking.consultant_user_id]:
            raise HTTPException(status_code=403, detail="Non autorizzato")
        
        # Se già fermato, non è un errore (potrebbe essere stato fermato dall'altro utente)
        if booking.recording_status != "recording":
            return {
                "success": True,
                "message": "Recording già fermato",
                "recording_url": booking.recording_url,
                "duration": booking.recording_duration
            }
        
        if not booking.recording_sid or not booking.recording_resource_id:
            raise HTTPException(status_code=400, detail="Dati recording mancanti")
        
        # Ferma recording
        recorder_uid = 0
        channel_name = f"booking_{booking_id}"
        
        result = stop_recording(
            booking.recording_resource_id,
            booking.recording_sid,
            channel_name,
            recorder_uid
        )
        
        if not result:
            booking.recording_status = "failed"
        else:
            # Genera URL per accedere al video
            file_name = result["file_name"]
            recording_url = get_recording_url(file_name)
            
            booking.recording_url = recording_url
            booking.recording_duration = result.get("mix_duration", 0)
            booking.recording_status = "completed"
            booking.recording_completed_at = datetime.utcnow()
        
        booking.updated_at = datetime.utcnow()
        session.add(booking)
        session.commit()
        
        return {
            "success": True,
            "recording_url": booking.recording_url,
            "duration": booking.recording_duration,
            "message": "Registrazione completata"
        }

@router.get("/api/booking/{booking_id}/recording")
async def get_booking_recording(booking_id: int, request: Request):
    """Ottiene info sulla registrazione"""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    with Session(engine) as session:
        booking = session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Prenotazione non trovata")
        
        # Solo client e consultant possono vedere recording
        if current_user.id not in [booking.client_user_id, booking.consultant_user_id]:
            raise HTTPException(status_code=403, detail="Non autorizzato")
        
        return {
            "booking_id": booking.id,
            "recording_status": booking.recording_status,
            "recording_url": booking.recording_url,
            "recording_duration": booking.recording_duration,
            "recording_file_size": booking.recording_file_size,
            "recording_started_at": booking.recording_started_at.isoformat() if booking.recording_started_at else None,
            "recording_completed_at": booking.recording_completed_at.isoformat() if booking.recording_completed_at else None
        }

@router.get("/booking/success", response_class=HTMLResponse)
async def booking_success(request: Request):
    """Payment success page"""
    current_user = get_current_user(request)
    return templates.TemplateResponse("booking_success.html", {
        "request": request,
        "user": current_user,
        "current_user": current_user
    })

@router.get("/booking/cancel", response_class=HTMLResponse)
async def booking_cancel(request: Request, offer_id: Optional[int] = None):
    """Payment cancelled page"""
    current_user = get_current_user(request)
    back_url = f"/consulenza/prenota/{offer_id}" if offer_id else "/profile"
    return templates.TemplateResponse("booking_cancel.html", {
        "request": request,
        "user": current_user,
        "current_user": current_user,
        "back_url": back_url
    })

@router.post("/api/booking/{booking_id}/refuse")
async def refuse_booking(booking_id: int, request: Request):
    """Consulente rifiuta una prenotazione"""
    from pydantic import BaseModel
    
    class RefuseRequest(BaseModel):
        reason: Optional[str] = None
    
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    body = await request.json()
    refuse_reason = body.get("reason", "")
    
    with Session(engine) as session:
        booking = session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Prenotazione non trovata")
        
        # Verifica che l'utente sia il consulente
        if booking.consultant_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Solo il consulente può rifiutare la prenotazione")
        
        # Verifica che lo stato sia refusabile
        if booking.status not in ['pending', 'confirmed']:
            raise HTTPException(status_code=400, detail="Non puoi rifiutare una prenotazione in questo stato")
        
        # ✅ Validazione: annullamento max 4 ore prima dell'inizio
        booking_datetime = datetime.combine(booking.booking_date, booking.start_time)
        now = datetime.utcnow()
        time_until_booking = (booking_datetime - now).total_seconds() / 3600  # in ore
        
        if time_until_booking < 4:
            raise HTTPException(status_code=400, detail="Puoi annullare la consulenza solo fino a 4 ore prima dell'inizio")
        
        # ✅ 1. Cambia lo stato
        booking.status = "cancelled"
        booking.cancellation_reason = refuse_reason or "Rifiutato dal consulente"
        booking.cancelled_by = current_user.id
        booking.cancelled_at = datetime.utcnow()
        session.add(booking)
        
        # ✅ 2. Rimborsa se il pagamento è avvenuto
        if booking.payment_status == 'paid' and booking.stripe_payment_intent_id:
            try:
                import stripe as stripe_module
                stripe_module.api_key = os.getenv("STRIPE_SECRET_KEY")
                
                # Effettua il rimborso
                refund = stripe_module.Refund.create(
                    payment_intent=booking.stripe_payment_intent_id,
                    reason='requested_by_customer'
                )
                logger.info(f"✅ Rimborso creato: {refund.id} per booking {booking_id}")
                booking.payment_status = "refunded"
            except stripe_module.error.InvalidRequestError as e:
                # Se la charge è già stata rimborsata, non è un errore
                if "already been refunded" in str(e):
                    logger.info(f"⚠️ Booking {booking_id} era già stato rimborsato prima")
                    booking.payment_status = "refunded"
                else:
                    logger.error(f"❌ Errore nel rimborso: {e}")
                    # Continua comunque, il rimborso manuale può essere fatto dopo
            except Exception as e:
                logger.error(f"❌ Errore nel rimborso: {e}")
                # Continua comunque, il rimborso manuale può essere fatto dopo
        
        session.commit()
        
        # ✅ 3. Invia notifica e email al cliente
        client = session.get(User, booking.client_user_id)
        consultant = session.get(User, booking.consultant_user_id)
        
        if client:
            client_name = f"{client.nome} {client.cognome}" if client.nome else "Cliente"
            consultant_name = f"{consultant.nome} {consultant.cognome}" if consultant and consultant.nome else "Il consulente"
            
            # Prepara la sezione motivo (opzionale)
            reason_section = ""
            if refuse_reason:
                reason_section = f"""
            <div style="background: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107; margin: 20px 0;">
                <p><strong>📝 Motivo del rifiuto:</strong></p>
                <p>{refuse_reason}</p>
            </div>
            """
            
            # Notifica nel sistema usando il servizio centralizzato
            send_notification(
                user_id=booking.client_user_id,
                type_key='booking_refused',
                title="Consulenza Rifiutata",
                message=f"{consultant_name} ha rifiutato la tua consulenza del {booking.booking_date.strftime('%d/%m/%Y')} alle {booking.start_time}",
                template_data={
                    'client_name': client_name,
                    'consultant_name': consultant_name,
                    'date': booking.booking_date.strftime('%d/%m/%Y'),
                    'time': booking.start_time,
                    'reason_section': reason_section,
                    'action_url': f"{os.getenv('BASE_URL', 'http://localhost:8080')}/profile#bookings"
                },
                related_booking_id=booking_id,
                action_url="/profile#bookings"
            )
        
        return {
            "success": True,
            "message": "Consulenza rifiutata con successo",
            "booking_id": booking_id,
            "refunded": booking.payment_status == "refunded"
        }


# ========== SCREEN SHARE STATE TRACKING ==========

# Variabile in-memory per tracciare lo stato di screen share per booking
# In produzione, usare Redis per multi-server
_screen_share_state = {}

@router.post("/api/booking/{booking_id}/screen-share/start")
async def screen_share_start(
    request: Request,
    booking_id: int
):
    """Notifica che un utente sta iniziando a condividere lo schermo - con state tracking"""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autorizzato")
    
    with Session(engine) as session:
        booking = session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Prenotazione non trovata")
        
        # Verifica che l'utente sia coinvolto nella prenotazione
        if current_user.id not in [booking.client_user_id, booking.consultant_user_id]:
            raise HTTPException(status_code=403, detail="Non autorizzato")
        
        # Traccia chi sta condividendo lo schermo
        _screen_share_state[booking_id] = {
            'is_sharing': True,
            'user_id': current_user.id,
            'timestamp': datetime.now(ITALY_TZ)
        }
        
        print(f"📺 Screen share avviato per booking {booking_id} da utente {current_user.id}")
        
        return {"success": True, "message": "Screen share avviato"}


@router.post("/api/booking/{booking_id}/screen-share/stop")
async def screen_share_stop(
    request: Request,
    booking_id: int
):
    """Notifica che un utente ha smesso di condividere lo schermo - con state tracking"""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autorizzato")
    
    with Session(engine) as session:
        booking = session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Prenotazione non trovata")
        
        # Verifica che l'utente sia coinvolto nella prenotazione
        if current_user.id not in [booking.client_user_id, booking.consultant_user_id]:
            raise HTTPException(status_code=403, detail="Non autorizzato")
        
        # Pulisci lo stato di screen share
        if booking_id in _screen_share_state:
            del _screen_share_state[booking_id]
        
        print(f"🎥 Screen share fermato per booking {booking_id} da utente {current_user.id}")
        
        return {"success": True, "message": "Screen share fermato"}


@router.get("/api/booking/{booking_id}/screen-share/status")
async def screen_share_status(
    request: Request,
    booking_id: int
):
    """Ottiene lo stato di screen share per il booking"""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autorizzato")
    
    with Session(engine) as session:
        booking = session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Prenotazione non trovata")
        
        # Verifica che l'utente sia coinvolto nella prenotazione
        if current_user.id not in [booking.client_user_id, booking.consultant_user_id]:
            raise HTTPException(status_code=403, detail="Non autorizzato")
        
        # Determina chi è l'altro utente
        other_user_id = booking.consultant_user_id if current_user.id == booking.client_user_id else booking.client_user_id
        
        # Controlla se c'è screen share attivo
        share_state = _screen_share_state.get(booking_id)
        
        # Se c'è screen share, verifica se è dell'altro utente
        is_remote_sharing = share_state is not None and share_state['user_id'] != current_user.id
        
        return {
            "booking_id": booking_id,
            "is_remote_sharing": is_remote_sharing,
            "sharing_user_id": share_state['user_id'] if share_state else None,
            "current_user_id": current_user.id
        }


# ========== CALL TIME VALIDATION ==========

@router.get("/api/booking/{booking_id}/call-status")
async def call_status(
    request: Request,
    booking_id: int
):
    """Verifica se la call è ancora attiva (non è scaduta)"""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autorizzato")
    
    with Session(engine) as session:
        booking = session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Prenotazione non trovata")
        
        # Verifica che l'utente sia coinvolto nella prenotazione
        if current_user.id not in [booking.client_user_id, booking.consultant_user_id]:
            raise HTTPException(status_code=403, detail="Non autorizzato")
        
        # Calcola l'orario di scadenza: end_time + 5 minuti
        now_italy = datetime.now(ITALY_TZ)
        
        # Combina booking_date + end_time (converte end_time da stringa a time)
        end_time_obj = datetime.strptime(booking.end_time, "%H:%M").time()
        end_datetime_naive = datetime.combine(booking.booking_date, end_time_obj)
        end_datetime = end_datetime_naive.replace(tzinfo=ITALY_TZ)
        call_deadline = end_datetime + timedelta(minutes=5)
        
        # Controlla se la call è scaduta
        is_expired = now_italy >= call_deadline
        
        # Secondi rimanenti
        remaining_seconds = int((call_deadline - now_italy).total_seconds())
        
        print(f"📞 Call status check - booking {booking_id}: now={now_italy}, deadline={call_deadline}, expired={is_expired}, remaining={remaining_seconds}s")
        
        return {
            "booking_id": booking_id,
            "is_active": not is_expired,
            "is_expired": is_expired,
            "remaining_seconds": max(0, remaining_seconds),
            "end_time": booking.end_time,
            "booking_date": booking.booking_date.isoformat()
        }


@router.post("/api/booking/{booking_id}/call-end")
async def call_end(
    request: Request,
    booking_id: int
):
    """Marca la call come terminata e aggiorna lo stato del booking"""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autorizzato")
    
    with Session(engine) as session:
        booking = session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Prenotazione non trovata")
        
        # Verifica che l'utente sia coinvolto nella prenotazione
        if current_user.id not in [booking.client_user_id, booking.consultant_user_id]:
            raise HTTPException(status_code=403, detail="Non autorizzato")
        
        # Calcola l'orario di scadenza: end_time + 5 minuti
        now_italy = datetime.now(ITALY_TZ)
        
        # Combina booking_date + end_time (converte end_time da stringa a time)
        end_time_obj = datetime.strptime(booking.end_time, "%H:%M").time()
        end_datetime_naive = datetime.combine(booking.booking_date, end_time_obj)
        end_datetime = end_datetime_naive.replace(tzinfo=ITALY_TZ)
        call_deadline = end_datetime + timedelta(minutes=5)
        
        # Controlla se il tempo è scaduto
        if now_italy >= call_deadline:
            print(f"✅ Call terminata per booking {booking_id} - deadline scaduto")
            # Pulisci lo stato di screen share se esiste
            if booking_id in _screen_share_state:
                del _screen_share_state[booking_id]
            
            return {
                "success": True,
                "message": "Call terminata",
                "booking_id": booking_id,
                "reason": "deadline_exceeded"
            }
        else:
            remaining_minutes = int((call_deadline - now_italy).total_seconds() / 60)
            print(f"⚠️ Tentativo di terminare call prematuramente - booking {booking_id}: {remaining_minutes} minuti rimasti")
            
            return {
                "success": False,
                "message": f"Call non può essere terminata - rimangono {remaining_minutes} minuti",
                "booking_id": booking_id,
                "reason": "time_remaining",
                "remaining_minutes": remaining_minutes
            }


@router.post("/api/booking/{booking_id}/call-start")
async def mark_call_started(
    request: Request,
    booking_id: int
):
    """Marca il momento in cui la call viene avviata (per permettere ripresa)"""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autorizzato")
    
    with Session(engine) as session:
        booking = session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Prenotazione non trovata")
        
        # Verifica che l'utente sia coinvolto nella prenotazione
        if current_user.id not in [booking.client_user_id, booking.consultant_user_id]:
            raise HTTPException(status_code=403, detail="Non autorizzato")
        
        # Marca il momento in cui la call è stata avviata (se non già marcata)
        if booking.call_started_at is None:
            booking.call_started_at = datetime.now(ITALY_TZ)
            session.add(booking)
            session.commit()
            print(f"📞 Call avviata per booking {booking_id} da utente {current_user.id}")
        
        return {
            "success": True,
            "call_started_at": booking.call_started_at.isoformat() if booking.call_started_at else None
        }


@router.get("/api/booking/{booking_id}/call-status-extended")
async def get_call_status_extended(
    request: Request,
    booking_id: int
):
    """Verifica stato della call: se scaduta, se già avviata, se può essere ripresa"""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autorizzato")
    
    with Session(engine) as session:
        booking = session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Prenotazione non trovata")
        
        # Verifica che l'utente sia coinvolto nella prenotazione
        if current_user.id not in [booking.client_user_id, booking.consultant_user_id]:
            raise HTTPException(status_code=403, detail="Non autorizzato")
        
        # Calcola deadline della call
        now_italy = datetime.now(ITALY_TZ)
        end_time_obj = datetime.strptime(booking.end_time, "%H:%M").time()
        end_datetime_naive = datetime.combine(booking.booking_date, end_time_obj)
        end_datetime = end_datetime_naive.replace(tzinfo=ITALY_TZ)
        call_deadline = end_datetime + timedelta(minutes=5)
        
        # Stato della call
        is_expired = now_italy >= call_deadline
        call_has_started = booking.call_started_at is not None
        can_resume = call_has_started and not is_expired
        
        remaining_seconds = int((call_deadline - now_italy).total_seconds()) if not is_expired else 0
        
        print(f"📞 Call status extended - booking {booking_id}: started={call_has_started}, expired={is_expired}, can_resume={can_resume}")
        
        return {
            "booking_id": booking_id,
            "is_expired": is_expired,
            "call_has_started": call_has_started,
            "can_resume": can_resume,
            "remaining_seconds": max(0, remaining_seconds),
            "call_started_at": booking.call_started_at.isoformat() if booking.call_started_at else None
        }


# ========== CALL CHAT ENDPOINTS ==========

@router.post("/api/booking/{booking_id}/chat/send")
async def send_call_message(
    booking_id: int,
    body: ChatMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """Invia un messaggio durante la call"""
    
    try:
        with Session(engine) as session:
            # Verifica che il booking esista e che l'utente sia parte della call
            booking = session.exec(
                select(Booking).where(Booking.id == booking_id)
            ).first()
            
            if not booking:
                raise HTTPException(status_code=404, detail="Booking non trovato")
            
            # Verifica che l'utente sia il client o il consultant
            if current_user.id not in [booking.client_user_id, booking.consultant_user_id]:
                raise HTTPException(status_code=403, detail="Non autorizzato")
            
            # Crea il messaggio
            call_msg = CallMessage(
                booking_id=booking_id,
                user_id=current_user.id,
                message=body.message.strip()
            )
            session.add(call_msg)
            session.commit()
            session.refresh(call_msg)
            
            # Ottieni l'utente per il nome
            user = session.exec(select(User).where(User.id == current_user.id)).first()
            
            logger.info(f"💬 Messaggio call inviato nel booking {booking_id} da {user.nome} {user.cognome}")
            
            return {
                "id": call_msg.id,
                "user_id": call_msg.user_id,
                "user_name": f"{user.nome} {user.cognome}" if user.nome and user.cognome else user.email,
                "message": call_msg.message,
                "created_at": call_msg.created_at.isoformat()
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Errore invio messaggio call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/booking/{booking_id}/chat/messages")
async def get_call_messages(
    booking_id: int,
    current_user: User = Depends(get_current_user)
):
    """Ottiene tutti i messaggi della call"""
    
    try:
        with Session(engine) as session:
            # Verifica che il booking esista e che l'utente sia parte della call
            booking = session.exec(
                select(Booking).where(Booking.id == booking_id)
            ).first()
            
            if not booking:
                raise HTTPException(status_code=404, detail="Booking non trovato")
            
            # Verifica che l'utente sia il client o il consultant
            if current_user.id not in [booking.client_user_id, booking.consultant_user_id]:
                raise HTTPException(status_code=403, detail="Non autorizzato")
            
            # Ottieni tutti i messaggi ordinati per data
            messages = session.exec(
                select(CallMessage)
                .where(CallMessage.booking_id == booking_id)
                .order_by(CallMessage.created_at)
            ).all()
            
            # Costruisci la risposta con info dell'utente
            messages_data = []
            for msg in messages:
                user = session.exec(select(User).where(User.id == msg.user_id)).first()
                messages_data.append({
                    "id": msg.id,
                    "user_id": msg.user_id,
                    "user_name": f"{user.nome} {user.cognome}" if user.nome and user.cognome else user.email,
                    "message": msg.message,
                    "created_at": msg.created_at.isoformat()
                })
            
            return {"messages": messages_data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Errore lettura messaggi call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== AUTO RECORDING ENDPOINTS ==========

@router.post("/api/booking/{booking_id}/leave")
async def leave_booking(booking_id: int, request: Request):
    """Segna che l'utente è uscito dalla call - ferma recording se nessuno rimane"""
    print(f"\n🔔 [LEAVE] Function called for booking {booking_id}")
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    print(f"🔔 [LEAVE] Current user: {current_user.email}")
    
    with Session(engine) as session:
        booking = session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Prenotazione non trovata")
        
        # Verifica che l'utente sia parte della prenotazione
        if current_user.id not in [booking.client_user_id, booking.consultant_user_id]:
            raise HTTPException(status_code=403, detail="Non autorizzato")
        
        # Segna l'uscita dell'utente
        is_client = booking.client_user_id == current_user.id
        now = datetime.now()
        
        print(f"🔔 [LEAVE] Booking found: {booking_id}, is_client={is_client}, recording_status={booking.recording_status}")
        logger.info(f"👋 User leaving booking {booking_id} (is_client={is_client})")
        
        if is_client:
            booking.client_joined_at = None
        else:
            booking.consultant_joined_at = None
        
        booking.updated_at = now
        
        # Controlla se rimane qualcuno in call
        client_still_in = booking.client_joined_at is not None
        consultant_still_in = booking.consultant_joined_at is not None
        anyone_in_call = client_still_in or consultant_still_in
        
        print(f"🔔 [LEAVE] After update - client_still_in={client_still_in}, consultant_still_in={consultant_still_in}, anyone_in_call={anyone_in_call}")
        logger.info(f"   - Client still in: {client_still_in}, Consultant still in: {consultant_still_in}, Anyone in: {anyone_in_call}")
        
        # 🎥 Se nessuno rimane in call e la registrazione è attiva, ferma
        if not anyone_in_call and booking.recording_status == "recording":
            print(f"🔔 [LEAVE] ✅ SHOULD STOP RECORDING: anyone_in_call={anyone_in_call}, recording_status={booking.recording_status}")
            logger.info(f"🎥 All users left - stopping recording for booking {booking_id}")
            try:
                from app.utils.agora_recording import stop_recording, get_recording_url
                import asyncio
                
                recorder_uid = 0
                channel_name = f"booking_{booking_id}"
                
                logger.info(
                    "🎯 Recording stop context | booking=%s resource_id=%s sid=%s channel=%s",
                    booking_id,
                    booking.recording_resource_id,
                    booking.recording_sid,
                    channel_name,
                )

                wait_seconds = 15
                print(
                    f"🔔 [LEAVE] ⏳ Waiting {wait_seconds} seconds before stopping recording (let Agora save to S3)..."
                )
                logger.info(f"⏳ Waiting {wait_seconds} seconds for Agora to flush recording to S3...")
                await asyncio.sleep(wait_seconds)

                print(
                    f"🔔 [LEAVE] Calling stop_recording with SID={booking.recording_sid}, ResourceID={booking.recording_resource_id}"
                )
                logger.info(
                    "🎥 Stopping recording for booking %s after wait of %ss",
                    booking_id,
                    wait_seconds,
                )
                
                result = stop_recording(
                    booking.recording_resource_id,
                    booking.recording_sid,
                    channel_name,
                    recorder_uid
                )
                
                print(f"🔔 [LEAVE] stop_recording result: {result}")
                
                if result:
                    file_name = result["file_name"]
                    recording_url = get_recording_url(file_name)
                    
                    booking.recording_url = recording_url
                    booking.recording_duration = result.get("mix_duration", 0)
                    booking.recording_status = "completed"
                    booking.recording_completed_at = now
                    
                    logger.info(f"✅ Recording stopped and saved: {recording_url}")
                else:
                    print(f"🔔 [LEAVE] ⚠️ Recording stop returned no result")
                    logger.warning(f"⚠️ Recording stop returned no result")
                    booking.recording_status = "failed"
                    
            except Exception as e:
                print(f"🔔 [LEAVE] ❌ Error: {e}")
                logger.error(f"❌ Error stopping recording for booking {booking_id}: {e}", exc_info=True)
                booking.recording_status = "failed"
        else:
            print(f"🔔 [LEAVE] ⚠️ NOT stopping recording: anyone_in_call={anyone_in_call}, recording_status={booking.recording_status}")
            if anyone_in_call:
                logger.info(f"ℹ️ User left but others still in call - keeping recording active")
            else:
                logger.info(f"ℹ️ Recording not active (status={booking.recording_status}) - nothing to stop")
        
        session.add(booking)
        session.commit()
        session.refresh(booking)
        
        print(f"🔔 [LEAVE] Booking saved - final recording_status={booking.recording_status}")
        
        return {
            "success": True,
            "has_left": True,
            "client_in_call": client_still_in,
            "consultant_in_call": consultant_still_in,
            "still_has_participants": anyone_in_call,
            "recording_status": booking.recording_status
        }
