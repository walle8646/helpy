from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from datetime import datetime, timedelta
from typing import Optional
from decimal import Decimal

from ..database import engine
from ..models import User, ConsultationOffer, Message
from .auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/consulenza/crea/{client_user_id}", response_class=HTMLResponse)
async def show_create_consultation_form(
    request: Request,
    client_user_id: int,
    user: User = Depends(get_current_user)
):
    """Show form for consultant to create a consultation offer"""
    
    with Session(engine) as session:
        # Verify current user is a consultant
        if user.category_id != 2:
            raise HTTPException(status_code=403, detail="Solo i consulenti possono creare offerte di consulenza")
        
        # Get client user
        client = session.get(User, client_user_id)
        if not client:
            raise HTTPException(status_code=404, detail="Cliente non trovato")
        
        # Check if there's already a pending offer
        existing_offer = session.exec(
            select(ConsultationOffer)
            .where(ConsultationOffer.consultant_user_id == user.id)
            .where(ConsultationOffer.client_user_id == client_user_id)
            .where(ConsultationOffer.status == "pending")
            .where(ConsultationOffer.expires_at > datetime.utcnow())
        ).first()
        
        return templates.TemplateResponse("create_consultation_offer.html", {
            "request": request,
            "user": user,
            "client": client,
            "existing_offer": existing_offer,
            "default_price": user.prezzo_consulenza or 50,
            "duration_options": [30, 60, 90, 120]
        })


@router.post("/consulenza/crea/{client_user_id}")
async def create_consultation_offer(
    request: Request,
    client_user_id: int,
    price: float = Form(...),
    duration_minutes: int = Form(...),
    custom_message: Optional[str] = Form(None),
    user: User = Depends(get_current_user)
):
    """Create a new consultation offer and send automated message"""
    
    with Session(engine) as session:
        # Verify current user is a consultant
        if user.category_id != 2:
            raise HTTPException(status_code=403, detail="Solo i consulenti possono creare offerte di consulenza")
        
        # Validate inputs
        if price <= 0:
            raise HTTPException(status_code=400, detail="Il prezzo deve essere maggiore di zero")
        
        if duration_minutes not in [30, 60, 90, 120]:
            raise HTTPException(status_code=400, detail="Durata non valida. Scegli tra 30, 60, 90 o 120 minuti")
        
        # Get client user
        client = session.get(User, client_user_id)
        if not client:
            raise HTTPException(status_code=404, detail="Cliente non trovato")
        
        # Expire any previous pending offers from this consultant to this client
        previous_offers = session.exec(
            select(ConsultationOffer)
            .where(ConsultationOffer.consultant_user_id == user.id)
            .where(ConsultationOffer.client_user_id == client_user_id)
            .where(ConsultationOffer.status == "pending")
        ).all()
        
        for offer in previous_offers:
            offer.status = "expired"
            offer.updated_at = datetime.utcnow()
            session.add(offer)
        
        # Create new consultation offer (expires in 7 days)
        new_offer = ConsultationOffer(
            consultant_user_id=user.id,
            client_user_id=client_user_id,
            price=price,
            duration_minutes=duration_minutes,
            status="pending",
            message=custom_message,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        session.add(new_offer)
        session.commit()
        session.refresh(new_offer)
    
        # Send automated message to client
        message_content = f"""🎯 **Offerta di Consulenza**

Ho creato un'offerta di consulenza per te:
• Durata: {duration_minutes} minuti
• Prezzo: €{price:.2f}"""
        
        if custom_message:
            message_content += f"\n• Messaggio: {custom_message}"
        
        message_content += f"""

[📅 Prenota ora](/consulenza/prenota/{new_offer.id})

_Questa offerta scade il {new_offer.expires_at.strftime('%d/%m/%Y alle %H:%M')}_"""
        
        # Get or create conversation between consultant and client
        from app.models import Conversation
        user1_id = min(user.id, client_user_id)
        user2_id = max(user.id, client_user_id)
        
        conversation = session.exec(
            select(Conversation)
            .where(Conversation.user1_id == user1_id)
            .where(Conversation.user2_id == user2_id)
        ).first()
        
        if not conversation:
            conversation = Conversation(
                user1_id=user1_id,
                user2_id=user2_id
            )
            session.add(conversation)
            session.commit()
            session.refresh(conversation)
        
        # Insert system message into conversation
        system_message = Message(
            conversation_id=conversation.id,
            sender_id=user.id,
            content=message_content,
            is_system_message=True,
            consultation_offer_id=new_offer.id
        )
        session.add(system_message)
        
        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        session.add(conversation)
        
        session.commit()
        
        # Return JSON response instead of redirect
        return JSONResponse({
            "success": True,
            "message": "Messaggio per la prenotazione inviato correttamente",
            "offer_id": new_offer.id,
            "client_user_id": client_user_id
        })



@router.get("/consulenza/prenota/{offer_id}", response_class=HTMLResponse)
async def show_booking_page(
    request: Request,
    offer_id: int,
    user: User = Depends(get_current_user)
):
    """Show booking page for client to book consultation"""
    
    with Session(engine) as session:
        # Get consultation offer
        offer = session.get(ConsultationOffer, offer_id)
        if not offer:
            raise HTTPException(status_code=404, detail="Offerta non trovata")
        
        # Verify user is the client
        if user.id != offer.client_user_id:
            raise HTTPException(status_code=403, detail="Non sei autorizzato a prenotare questa consulenza")
        
        # Check if offer is still valid
        if offer.status != "pending":
            raise HTTPException(status_code=400, detail=f"Questa offerta non è più disponibile (stato: {offer.status})")
        
        if offer.expires_at < datetime.utcnow():
            offer.status = "expired"
            offer.updated_at = datetime.utcnow()
            session.add(offer)
            session.commit()
            raise HTTPException(status_code=400, detail="Questa offerta è scaduta")
        
        # Get consultant
        consultant = session.get(User, offer.consultant_user_id)
        if not consultant:
            raise HTTPException(status_code=404, detail="Consulente non trovato")
        
        return templates.TemplateResponse("book_consultation_offer.html", {
            "request": request,
            "user": user,
            "offer": offer,
            "consultant": consultant
        })


@router.get("/api/consultation-offers/{offer_id}")
async def get_consultation_offer(
    offer_id: int,
    user: User = Depends(get_current_user)
):
    """Get consultation offer details (API endpoint)"""
    
    with Session(engine) as session:
        offer = session.get(ConsultationOffer, offer_id)
        if not offer:
            raise HTTPException(status_code=404, detail="Offerta non trovata")
        
        # Verify user is either consultant or client
        if user.id not in [offer.consultant_user_id, offer.client_user_id]:
            raise HTTPException(status_code=403, detail="Non autorizzato")
        
        consultant = session.get(User, offer.consultant_user_id)
        client = session.get(User, offer.client_user_id)
        
        return JSONResponse({
            "id": offer.id,
            "consultant": {
                "id": consultant.id,
                "nome": consultant.nome,
                "cognome": consultant.cognome,
                "profile_picture": consultant.profile_picture
            },
            "client": {
                "id": client.id,
                "nome": client.nome,
                "cognome": client.cognome
            },
            "price": offer.price,
            "duration_minutes": offer.duration_minutes,
            "status": offer.status,
            "message": offer.message,
            "expires_at": offer.expires_at.isoformat(),
            "created_at": offer.created_at.isoformat()
        })


@router.post("/consulenza/prenota/{offer_id}/confirm")
async def confirm_booking(
    request: Request,
    offer_id: int,
    user: User = Depends(get_current_user)
):
    """Create Stripe Checkout Session for consultation booking"""
    from app.utils.stripe_config import create_checkout_session
    import json
    import os
    
    # Get slot data from request body
    body = await request.json()
    selected_date = body.get('date')
    start_time = body.get('start_time')
    end_time = body.get('end_time')
    
    if not selected_date or not start_time or not end_time:
        raise HTTPException(status_code=400, detail="Dati slot mancanti")
    
    with Session(engine) as session:
        # Get consultation offer
        offer = session.get(ConsultationOffer, offer_id)
        if not offer:
            raise HTTPException(status_code=404, detail="Offerta non trovata")
        
        # Verify user is the client
        if user.id != offer.client_user_id:
            raise HTTPException(status_code=403, detail="Non sei autorizzato")
        
        # Check if offer is still valid
        if offer.status != "pending":
            raise HTTPException(status_code=400, detail="Questa offerta non è più disponibile")
        
        if offer.expires_at < datetime.utcnow():
            offer.status = "expired"
            session.add(offer)
            session.commit()
            raise HTTPException(status_code=400, detail="Questa offerta è scaduta")
        
        # Get APP_URL from environment
        app_url = os.getenv("BASE_URL", "http://localhost:8080")
        
        # Create Stripe Checkout Session
        try:
            # Convert price to cents (Stripe uses smallest currency unit)
            amount_cents = int(float(offer.price) * 100)
            
            checkout_session = create_checkout_session(
                amount=amount_cents,
                currency='eur',
                success_url=f"{app_url}/booking/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{app_url}/consulenza/prenota/{offer_id}?cancelled=true",
                metadata={
                    'offer_id': str(offer.id),
                    'client_user_id': str(offer.client_user_id),
                    'consultant_user_id': str(offer.consultant_user_id),
                    'selected_date': selected_date,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration_minutes': str(offer.duration_minutes)
                }
            )
            
            return JSONResponse({
                "success": True,
                "checkout_url": checkout_session.url,
                "session_id": checkout_session.id
            })
            
        except Exception as e:
            logger.error(f"Error creating Stripe checkout session: {e}")
            raise HTTPException(status_code=500, detail=f"Errore nella creazione del pagamento: {str(e)}")


