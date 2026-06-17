"""
Routes per il sistema di recensioni post-consulenza.
"""
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel import Session, select
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pydantic import BaseModel, Field
from typing import Optional
import secrets
import os

from app.database import engine
from app.models import Review, Booking, User
from app.routes.auth import get_current_user
from app.logger_config import logger
from app.utils.notification_service import send_notification
from app.utils_user import get_display_name

router = APIRouter()

ITALY_TZ = ZoneInfo("Europe/Rome")


class ReviewRequest(BaseModel):
    rating_helpful: int = Field(ge=1, le=5)
    rating_prepared: int = Field(ge=1, le=5)
    rating_communication: int = Field(ge=1, le=5)
    comment: Optional[str] = None


@router.post("/api/booking/{booking_id}/review")
async def submit_review(booking_id: int, review_data: ReviewRequest, request: Request):
    """Invia una recensione per una consulenza completata"""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autenticato")

    with Session(engine) as session:
        booking = session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Prenotazione non trovata")

        # Solo il cliente può lasciare una recensione
        if current_user.id != booking.client_user_id:
            raise HTTPException(status_code=403, detail="Solo il cliente può lasciare una recensione")

        # Controlla se esiste già una recensione per questo booking
        existing = session.exec(
            select(Review).where(Review.booking_id == booking_id)
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Hai già lasciato una recensione per questa consulenza")

        review = Review(
            booking_id=booking_id,
            reviewer_user_id=current_user.id,
            consultant_user_id=booking.consultant_user_id,
            rating_helpful=review_data.rating_helpful,
            rating_prepared=review_data.rating_prepared,
            rating_communication=review_data.rating_communication,
            comment=review_data.comment.strip() if review_data.comment else None,
        )
        session.add(review)
        session.commit()
        session.refresh(review)

        logger.info(f"⭐ Review creata per booking {booking_id} da user {current_user.id}")

        # 🔔 Notifica al consulente: ha ricevuto una recensione (in-app + email)
        try:
            consultant = session.get(User, booking.consultant_user_id)
            reviewer = session.get(User, current_user.id)
            reviewer_name = get_display_name(reviewer) if reviewer else "Un cliente"
            consultant_name = (f"{consultant.nome or ''} {consultant.cognome or ''}").strip() if consultant else ""
            avg_rating = round(
                (review.rating_helpful + review.rating_prepared + review.rating_communication) / 3, 1
            )
            date_str = booking.booking_date.strftime("%d/%m/%Y") if booking.booking_date else ""
            send_notification(
                user_id=booking.consultant_user_id,
                type_key="review_received",
                title="Hai ricevuto una recensione ⭐",
                message=f"{reviewer_name} ti ha lasciato una recensione ({avg_rating}/5) per la consulenza del {date_str}.",
                template_data={
                    "consultant_name": consultant_name or "Consulente",
                    "reviewer_name": reviewer_name,
                    "rating": str(avg_rating),
                    "date": date_str,
                    "comment": review.comment or "",
                    "action_url": f"{os.getenv('BASE_URL', '')}/user/{booking.consultant_user_id}",
                },
                related_booking_id=booking_id,
                action_url=f"/user/{booking.consultant_user_id}",
            )
        except Exception as e:
            logger.error(f"Errore invio notifica recensione al consulente: {e}")

        return JSONResponse({"success": True, "message": "Recensione inviata con successo!"})


@router.post("/api/booking/{booking_id}/review/send-email")
async def send_review_email(booking_id: int, request: Request, background_tasks: BackgroundTasks):
    """Invia un'email al cliente con il link per votare più tardi"""
    logger.info(f"📧 [review] send-email chiamato per booking {booking_id}")
    current_user = get_current_user(request)
    if not current_user:
        logger.warning(f"📧 [review] Utente non autenticato")
        raise HTTPException(status_code=401, detail="Non autenticato")

    logger.info(f"📧 [review] User {current_user.id} ({current_user.email}) richiede email review per booking {booking_id}")

    with Session(engine) as session:
        booking = session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Prenotazione non trovata")

        if current_user.id != booking.client_user_id:
            logger.warning(f"📧 [review] User {current_user.id} non è il client del booking {booking_id} (client_id={booking.client_user_id})")
            raise HTTPException(status_code=403, detail="Non autorizzato")

        # Controlla se esiste già una recensione
        existing = session.exec(
            select(Review).where(Review.booking_id == booking_id)
        ).first()
        if existing:
            return JSONResponse({"success": False, "message": "Hai già lasciato una recensione"})

        # Genera token univoco per il link email
        token = secrets.token_urlsafe(32)

        consultant = session.get(User, booking.consultant_user_id)
        consultant_name = f"{consultant.nome} {consultant.cognome}" if consultant and consultant.nome else "il consulente"

        base_url = os.getenv('BASE_URL', 'http://localhost:8080')
        review_url = f"{base_url}/review/{token}?booking_id={booking_id}"

        # Dati per i task in background
        client_user_id = current_user.id
        client_nome = current_user.nome or current_user.email.split('@')[0]
        booking_date_str = booking.booking_date.strftime('%d/%m/%Y')
        booking_start_time = booking.start_time

    # Schedula email e reminder in background (così la risposta arriva subito)
    def _send_email_and_schedule():
        try:
            from app.scheduler import schedule_review_reminder
            reminder_time = datetime.now(ITALY_TZ) + timedelta(hours=24)
            schedule_review_reminder(booking_id, client_user_id, token, reminder_time)
            logger.info(f"📧 [review] Reminder schedulato per booking {booking_id}")
        except Exception as e:
            logger.error(f"📧 [review] Errore scheduling reminder: {e}")

        try:
            send_notification(
                user_id=client_user_id,
                type_key='review_request',
                title='Lascia una recensione',
                message=f'Scrivi una recensione per la tua consulenza con {consultant_name}',
                template_data={
                    'user_name': client_nome,
                    'consultant_name': consultant_name,
                    'review_url': review_url,
                    'date': booking_date_str,
                    'time': booking_start_time,
                },
                related_booking_id=booking_id,
                action_url=review_url
            )
            logger.info(f"📧 [review] Email notification inviata con successo")
        except Exception as e:
            logger.error(f"📧 [review] Errore invio email: {e}")

    background_tasks.add_task(_send_email_and_schedule)

    logger.info(f"📧 [review] Ritorno risposta success per booking {booking_id}")
    return JSONResponse({"success": True, "message": "Email inviata! Controlla la tua casella di posta."})


@router.get("/review/{token}", response_class=HTMLResponse)
async def review_page(token: str, request: Request, booking_id: Optional[int] = None):
    """Pagina standalone per lasciare una recensione via link email"""
    with Session(engine) as session:
        # Cerca se esiste già una review con questo token (completata)
        existing_review = session.exec(
            select(Review).where(Review.review_token == token)
        ).first()
        if existing_review:
            return request.app.state.templates.TemplateResponse("review.html", {
                "request": request,
                "already_reviewed": True,
                "error": None,
                "booking": None,
                "consultant": None,
                "token": token,
            })

        # Cerchiamo il booking dal parametro
        if not booking_id:
            return request.app.state.templates.TemplateResponse("review.html", {
                "request": request,
                "error": "Link non valido",
                "already_reviewed": False,
                "booking": None,
                "consultant": None,
                "token": token,
            })

        booking = session.get(Booking, booking_id)
        if not booking:
            return request.app.state.templates.TemplateResponse("review.html", {
                "request": request,
                "error": "Prenotazione non trovata",
                "already_reviewed": False,
                "booking": None,
                "consultant": None,
                "token": token,
            })

        # Controlla se esiste già una review per questo booking
        existing_by_booking = session.exec(
            select(Review).where(Review.booking_id == booking_id)
        ).first()
        if existing_by_booking:
            return request.app.state.templates.TemplateResponse("review.html", {
                "request": request,
                "already_reviewed": True,
                "error": None,
                "booking": None,
                "consultant": None,
                "token": token,
            })

        consultant = session.get(User, booking.consultant_user_id)

        return request.app.state.templates.TemplateResponse("review.html", {
            "request": request,
            "booking": booking,
            "consultant": consultant,
            "token": token,
            "error": None,
            "already_reviewed": False,
        })


@router.post("/api/review/{token}/submit")
async def submit_review_by_token(token: str, review_data: ReviewRequest, booking_id: Optional[int] = None):
    """Invia una recensione tramite token (da link email)"""
    with Session(engine) as session:
        if not booking_id:
            raise HTTPException(status_code=400, detail="booking_id richiesto")

        booking = session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Prenotazione non trovata")

        # Controlla se esiste già una recensione
        existing = session.exec(
            select(Review).where(Review.booking_id == booking_id)
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Recensione già presente per questa consulenza")

        review = Review(
            booking_id=booking_id,
            reviewer_user_id=booking.client_user_id,
            consultant_user_id=booking.consultant_user_id,
            rating_helpful=review_data.rating_helpful,
            rating_prepared=review_data.rating_prepared,
            rating_communication=review_data.rating_communication,
            comment=review_data.comment.strip() if review_data.comment else None,
            review_token=token,
        )
        session.add(review)
        session.commit()

        logger.info(f"⭐ Review via token creata per booking {booking_id}")
        return JSONResponse({"success": True, "message": "Recensione inviata con successo! Grazie!"})
