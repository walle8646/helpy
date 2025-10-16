from fastapi import APIRouter, Request, Form, Cookie
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from app.models_user import User
from app.database import get_session
from app.auth import verify_token
from app.logger_config import logger
from typing import Optional

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/profile", response_class=HTMLResponse)
def user_profile(request: Request):
    session_token = request.cookies.get("session_token")
    logger.info(f"Profile accessed, cookie: {session_token[:20] if session_token else 'None'}...")
    
    if not session_token:
        logger.warning("No session token found, redirecting to login")
        return RedirectResponse("/login")
    
    try:
        payload = verify_token(session_token)
        user_id = payload.get("user_id")
        logger.info(f"Token verified, user_id: {user_id}")
        
        if not user_id:
            logger.warning("No user_id in token")
            return RedirectResponse("/login")
        
        with get_session() as session:
            user = session.get(User, user_id)
            if not user:
                logger.warning(f"User {user_id} not found in database")
                return RedirectResponse("/login")
            
            logger.info(f"User {user.email} loaded successfully")
            
            # Converti macro_aree e aree_interesse da stringa a lista
            macro_aree_list = user.macro_aree.split(',') if user.macro_aree else []
            aree_interesse_list = user.aree_interesse.split(',') if user.aree_interesse else []
            
            return templates.TemplateResponse("profile.html", {
                "request": request,
                "user": user,
                "macro_aree_list": macro_aree_list,
                "aree_interesse_list": aree_interesse_list
            })
    except Exception as e:
        logger.error(f"Error in profile: {e}")
        return RedirectResponse("/login")

@router.post("/api/update-profile")
def update_profile(
    request: Request,
    nome: Optional[str] = Form(None),
    professione: Optional[str] = Form(None),
    descrizione: Optional[str] = Form(None),
    macro_aree: Optional[str] = Form(None),
    aree_interesse: Optional[str] = Form(None),
    prezzo_consulenza: Optional[int] = Form(None),
    durata_consulenza: Optional[int] = Form(None)
):
    # Leggi il token dal cookie della request
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    try:
        payload = verify_token(session_token)
        user_id = payload.get("user_id")
        
        if not user_id:
            return JSONResponse({"error": "Invalid token"}, status_code=401)
        
        with get_session() as session:
            user = session.get(User, user_id)
            if not user:
                return JSONResponse({"error": "User not found"}, status_code=404)
            
            # Aggiorna solo i campi che sono stati inviati
            if nome is not None:
                user.nome = nome
            if professione is not None:
                user.professione = professione
            if descrizione is not None:
                user.descrizione = descrizione
            if macro_aree is not None:
                user.macro_aree = macro_aree
            if aree_interesse is not None:
                user.aree_interesse = aree_interesse
            if prezzo_consulenza is not None:
                user.prezzo_consulenza = prezzo_consulenza
            if durata_consulenza is not None:
                user.durata_consulenza = durata_consulenza
            
            session.add(user)
            session.commit()
            session.refresh(user)
            
            logger.info(f"Profile updated for user: {user.email}")
            
            return JSONResponse({"message": "Profile updated successfully"}, status_code=200)
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return JSONResponse({"error": "Failed to update profile"}, status_code=500)