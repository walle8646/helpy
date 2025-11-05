from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func
from datetime import datetime, timedelta, time
from typing import Optional, List, Dict, Union
from app.database import engine
from app.models import Booking, User, AvailabilityBlock
from app.routes.auth import get_current_user
from app.utils.agora_recording import start_recording, stop_recording, get_recording_url

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# ========== UTILITÀ ==========

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
    
    for block in availability_blocks:
        # Converti start_time e end_time in minuti
        block_start = parse_time_to_minutes(block.start_time)
        block_end = parse_time_to_minutes(block.end_time)
        
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
                available_slots.append({
                    'start_time': minutes_to_time(current_time),
                    'end_time': minutes_to_time(current_time + duration_minutes),
                    'availability_block_id': block.id
                })
                current_time += 30  # Incremento di 30 minuti per slot successivo
            
            # Salta l'intervallo occupato
            current_time = max(current_time, occupied_end)
        
        # Slot disponibili dopo l'ultimo intervallo occupato
        while current_time + duration_minutes <= block_end:
            available_slots.append({
                'start_time': minutes_to_time(current_time),
                'end_time': minutes_to_time(current_time + duration_minutes),
                'availability_block_id': block.id
            })
            current_time += 30
    
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
        
        # Non si può prenotare nel passato
        if target_date < datetime.now().date():
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
    Crea una nuova prenotazione.
    
    Body:
        consultant_user_id: int
        booking_date: str (YYYY-MM-DD)
        start_time: str (HH:MM)
        end_time: str (HH:MM)
        duration_minutes: int
        availability_block_id: int (optional)
        client_notes: str (optional)
    """
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
    
    # Validazioni
    if not all([consultant_id, booking_date_str, start_time, end_time, duration_minutes]):
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
        
        # Calcola il prezzo
        price = consultant.prezzo_consulenza if consultant.prezzo_consulenza else 0
        
        # Crea la prenotazione
        new_booking = Booking(
            client_user_id=current_user.id,
            consultant_user_id=consultant_id,
            availability_block_id=availability_block_id,
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            status='pending',
            price=price,
            payment_status='pending',
            client_notes=client_notes
        )
        
        session.add(new_booking)
        session.commit()
        session.refresh(new_booking)
        
        return {
            "success": True,
            "booking_id": new_booking.id,
            "message": "Prenotazione creata con successo",
            "booking": {
                "id": new_booking.id,
                "date": booking_date_str,
                "start_time": start_time,
                "end_time": end_time,
                "consultant_name": f"{consultant.nome} {consultant.cognome}",
                "price": float(price) if price else 0,
                "status": new_booking.status
            }
        }

@router.get("/api/booking/my-bookings")
async def get_my_bookings(
    request: Request
):
    """Restituisce tutte le prenotazioni dell'utente corrente (come cliente o consulente)"""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    with Session(engine) as session:
        # Prenotazioni come cliente
        bookings_as_client = session.exec(
            select(Booking)
            .where(Booking.client_user_id == current_user.id)
            .order_by(Booking.booking_date.desc())
        ).all()
        
        # Prenotazioni come consulente
        bookings_as_consultant = session.exec(
            select(Booking)
            .where(Booking.consultant_user_id == current_user.id)
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
        
        # Query per prenotazioni confermate FUTURE (dopo adesso)
        statement = select(Booking).where(
            (Booking.client_user_id == current_user.id) | (Booking.consultant_user_id == current_user.id),
            Booking.status.in_(['confirmed', 'pending'])
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
        
        return {
            "success": True,
            "has_joined": True,
            "other_joined": consultant_joined if is_client else client_joined,
            "can_start_call": client_joined and consultant_joined
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
        from app.utils.agora_token import generate_agora_token
        from agora_token import RtcTokenBuilder, Role_Publisher
        
        recorder_uid = 999999  # UID fisso per il bot recorder
        channel_name = f"booking_{booking_id}"
        recorder_token = generate_agora_token(channel_name, recorder_uid, Role_Publisher, 7200)
        
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
                recorder_uid = 999999
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
        recorder_uid = 999999
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
