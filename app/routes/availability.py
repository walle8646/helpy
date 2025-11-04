"""Route per gestione disponibilità consulenze"""
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func
from datetime import datetime, timedelta, date
from typing import List, Optional
import logging

from app.database import engine
from app.models import User, AvailabilityBlock
from app.routes.auth import verify_token

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)

@router.get("/availability", response_class=HTMLResponse)
async def availability_page(request: Request):
    """Pagina gestione disponibilità"""
    user = verify_token(request)
    if not user:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Devi effettuare il login per accedere a questa pagina"
        })
    
    return templates.TemplateResponse("availability.html", {
        "request": request,
        "user": user,
        "current_user": user
    })

@router.get("/api/availability/{date_str}")
async def get_availability_by_date(request: Request, date_str: str):
    """Ottieni disponibilità per una specifica data (formato: YYYY-MM-DD)"""
    user = verify_token(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non autorizzato")
    
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato data non valido")
    
    with Session(engine) as session:
        # Usa confronto con cast a DATE per SQLite compatibility
        statement = select(AvailabilityBlock).where(
            AvailabilityBlock.user_id == user.id,
            func.date(AvailabilityBlock.date) == date_str,
            AvailabilityBlock.is_active == True
        ).order_by(AvailabilityBlock.start_time)
        
        blocks = session.exec(statement).all()
        
        logger.info(f"📅 Loading availability for {date_str}: found {len(blocks)} blocks")
        
        return JSONResponse({
            "success": True,
            "date": date_str,
            "blocks": [
                {
                    "id": block.id,
                    "start_time": block.start_time.strftime("%H:%M") if block.start_time else None,
                    "end_time": block.end_time.strftime("%H:%M") if block.end_time else None,
                    "status": block.status
                }
                for block in blocks
            ]
        })

@router.post("/api/availability/save")
async def save_availability(
    request: Request,
    date: str = Form(...),
    blocks: str = Form(...)  # JSON string con array di blocchi
):
    """Salva disponibilità per una data specifica"""
    user = verify_token(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non autorizzato")
    
    try:
        import json
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
        blocks_data = json.loads(blocks)
        
        with Session(engine) as session:
            # Rimuovi blocchi esistenti per quella data
            existing = session.exec(
                select(AvailabilityBlock).where(
                    AvailabilityBlock.user_id == user.id,
                    func.date(AvailabilityBlock.date) == date
                )
            ).all()
            
            for block in existing:
                session.delete(block)
            
            # Crea nuovi blocchi
            for block_data in blocks_data:
                start_time = block_data["start_time"]
                end_time = block_data["end_time"]
                
                # Calcola durata in minuti
                start_parts = list(map(int, start_time.split(":")))
                end_parts = list(map(int, end_time.split(":")))
                start_minutes = start_parts[0] * 60 + start_parts[1]
                end_minutes = end_parts[0] * 60 + end_parts[1]
                total_minutes = end_minutes - start_minutes
                
                if total_minutes <= 0:
                    continue
                
                new_block = AvailabilityBlock(
                    user_id=user.id,
                    date=target_date,
                    start_time=start_time,
                    end_time=end_time,
                    total_minutes=total_minutes,
                    status="available"
                )
                session.add(new_block)
                logger.info(f"💾 Saving block: date={target_date} (type: {type(target_date)}), time={start_time}-{end_time}")
            
            session.commit()
            logger.info(f"✅ Saved {len(blocks_data)} availability blocks for user {user.id} on {date}")
            
            return JSONResponse({
                "success": True,
                "message": f"Disponibilità salvata per {date}"
            })
    
    except Exception as e:
        logger.error(f"❌ Error saving availability: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/availability/copy")
async def copy_availability(
    request: Request,
    source_date: str = Form(...),
    target_dates: str = Form(...)  # JSON array di date target
):
    """Copia disponibilità da una data sorgente a più date target"""
    user = verify_token(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non autorizzato")
    
    try:
        import json
        target_dates_list = json.loads(target_dates)
        
        with Session(engine) as session:
            # Ottieni blocchi dalla data sorgente
            source_blocks = session.exec(
                select(AvailabilityBlock).where(
                    AvailabilityBlock.user_id == user.id,
                    func.date(AvailabilityBlock.date) == source_date,
                    AvailabilityBlock.is_active == True
                )
            ).all()
            
            if not source_blocks:
                return JSONResponse({
                    "success": False,
                    "message": "Nessuna disponibilità trovata nella data sorgente"
                })
            
            copied_count = 0
            
            for target_date_str in target_dates_list:
                target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
                
                # Rimuovi blocchi esistenti
                existing = session.exec(
                    select(AvailabilityBlock).where(
                        AvailabilityBlock.user_id == user.id,
                        func.date(AvailabilityBlock.date) == target_date_str
                    )
                ).all()
                
                for block in existing:
                    session.delete(block)
                
                # Copia blocchi
                for source_block in source_blocks:
                    new_block = AvailabilityBlock(
                        user_id=user.id,
                        date=target_date,
                        start_time=source_block.start_time,
                        end_time=source_block.end_time,
                        total_minutes=source_block.total_minutes,
                        status="available"
                    )
                    session.add(new_block)
                    copied_count += 1
            
            session.commit()
            logger.info(f"✅ Copied availability from {source_date} to {len(target_dates_list)} dates")
            
            return JSONResponse({
                "success": True,
                "message": f"Disponibilità copiata in {len(target_dates_list)} giorni ({copied_count} blocchi totali)"
            })
    
    except Exception as e:
        logger.error(f"❌ Error copying availability: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/availability/block/{block_id}")
async def delete_availability_block(request: Request, block_id: int):
    """Elimina un blocco di disponibilità"""
    user = verify_token(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non autorizzato")
    
    with Session(engine) as session:
        block = session.get(AvailabilityBlock, block_id)
        
        if not block or block.user_id != user.id:
            raise HTTPException(status_code=404, detail="Blocco non trovato")
        
        session.delete(block)
        session.commit()
        
        return JSONResponse({
            "success": True,
            "message": "Blocco eliminato"
        })
