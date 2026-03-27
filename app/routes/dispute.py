"""
Routes per il sistema di contestazioni post-consulenza.
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from datetime import datetime
from zoneinfo import ZoneInfo
from pydantic import BaseModel, Field

from app.database import engine
from app.models import Dispute, DisputeMessage, Booking
from app.routes.auth import get_current_user
from app.logger_config import logger

router = APIRouter()

ITALY_TZ = ZoneInfo("Europe/Rome")


class DisputeRequest(BaseModel):
    description: str = Field(min_length=20, max_length=5000)


@router.post("/api/booking/{booking_id}/dispute")
async def open_dispute(booking_id: int, data: DisputeRequest, request: Request):
    """Apri una contestazione per una consulenza"""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Non autenticato")

    with Session(engine) as session:
        booking = session.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Prenotazione non trovata")

        if current_user.id != booking.client_user_id:
            raise HTTPException(status_code=403, detail="Solo il cliente può aprire una contestazione")

        # Controlla se esiste già una contestazione per questo booking
        existing = session.exec(
            select(Dispute).where(Dispute.booking_id == booking_id)
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Hai già aperto una contestazione per questa consulenza")

        dispute = Dispute(
            booking_id=booking_id,
            client_user_id=current_user.id,
            consultant_user_id=booking.consultant_user_id,
            description=data.description,
            status="open",
            created_at=datetime.now(ITALY_TZ),
        )
        session.add(dispute)
        session.commit()
        session.refresh(dispute)

        logger.info(f"🚨 [dispute] Contestazione #{dispute.id} aperta per booking {booking_id} da user {current_user.id}")

        return JSONResponse({"success": True, "dispute_id": dispute.id, "message": "Contestazione aperta con successo"})
