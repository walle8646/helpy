from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.database import get_session
from app.models import User, Category
from sqlmodel import select
from app.routes.auth import verify_token
from app.logger_config import logger
from typing import Optional
import os
import hashlib
from PIL import Image
import io

router = APIRouter()

@router.get("/profile", response_class=HTMLResponse)
async def user_profile(request: Request):
    """Pagina profilo utente"""
    try:
        user = verify_token(request)
        
        if not user:
            logger.warning("❌ Unauthorized access to profile")
            return RedirectResponse("/login", status_code=307)
        
        with get_session() as session:
            fresh_user = session.get(User, user.id)
            
            if not fresh_user:
                logger.error(f"❌ User ID {user.id} not found in database")
                request.session.clear()
                return RedirectResponse("/login", status_code=307)
            
            categories = session.exec(select(Category)).all()
            logger.info(f"✅ Loaded {len(categories)} categories")
            
            # ✅ AGGIUNGI cognome
            user_data = {
                "id": fresh_user.id,
                "email": fresh_user.email,
                "nome": fresh_user.nome or "",
                "cognome": fresh_user.cognome or "",  # ✅ AGGIUNGI questo
                "professione": fresh_user.professione or "",
                "descrizione": fresh_user.descrizione or "",
                "profile_picture": fresh_user.profile_picture or "/static/default-avatar.png",
                "category_id": fresh_user.category_id,
                "aree_interesse": fresh_user.aree_interesse or "",
                "prezzo_consulenza": fresh_user.prezzo_consulenza or 0,
                "bollini": fresh_user.bollini or 0,
                "confirmed": fresh_user.confirmed,
                "created_at": fresh_user.created_at.strftime("%d/%m/%Y") if fresh_user.created_at else "N/A"
            }
            
            logger.info(f"✅ Profile loaded for user: {fresh_user.email}")
            
            return request.app.state.templates.TemplateResponse(
                "profile.html",
                {
                    "request": request,
                    "user": user_data,
                    "categories": categories
                }
            )
    
    except Exception as e:
        logger.error(f"Error in profile: {e}", exc_info=True)
        request.session.clear()
        return RedirectResponse("/login", status_code=307)

@router.post("/api/profile/update")
async def update_profile(
    request: Request,
    nome: str = Form(None),
    cognome: str = Form(None),  # ✅ AGGIUNGI cognome
    professione: str = Form(None),
    descrizione: str = Form(None),
    category_id: Optional[int] = Form(None),
    aree_interesse: str = Form(None),
    prezzo_consulenza: Optional[int] = Form(None)
):
    """Aggiorna profilo utente"""
    try:
        user = verify_token(request)
        
        if not user:
            return JSONResponse({"error": "Non autenticato"}, status_code=401)
        
        with get_session() as session:
            db_user = session.get(User, user.id)
            
            if not db_user:
                return JSONResponse({"error": "Utente non trovato"}, status_code=404)
            
            if nome is not None:
                db_user.nome = nome
            if cognome is not None:  # ✅ AGGIUNGI questo
                db_user.cognome = cognome
            if professione is not None:
                db_user.professione = professione
            if descrizione is not None:
                db_user.descrizione = descrizione
            if category_id is not None:
                db_user.category_id = category_id
            if aree_interesse is not None:
                db_user.aree_interesse = aree_interesse
            if prezzo_consulenza is not None:
                db_user.prezzo_consulenza = prezzo_consulenza
            
            session.add(db_user)
            session.commit()
            session.refresh(db_user)
            
            logger.info(f"✅ Profile updated for user: {db_user.email}")
            
            return JSONResponse({
                "message": "Profilo aggiornato con successo!",
                "user": {
                    "nome": db_user.nome,
                    "cognome": db_user.cognome,  # ✅ AGGIUNGI questo
                    "professione": db_user.professione
                }
            })
    
    except Exception as e:
        logger.error(f"Error updating profile: {e}", exc_info=True)
        return JSONResponse(
            {"error": "Errore durante l'aggiornamento"},
            status_code=500
        )