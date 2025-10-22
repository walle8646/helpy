from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from app.models_user import User
from app.models_category import Category
from app.database import get_session
from app.auth import verify_token
from app.logger_config import logger
from typing import Optional
import os
import uuid
from pathlib import Path

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
        
        # 🔥 USA WITH per il context manager
        with get_session() as session:
            user = session.get(User, user_id)
            if not user:
                logger.warning(f"User {user_id} not found in database")
                return RedirectResponse("/login")
            
            # CARICA TUTTE LE CATEGORIE
            categories = session.exec(select(Category)).all()
            logger.info(f"✅ Loaded {len(categories)} categories: {[c.name for c in categories]}")
            
            # Carica la categoria dell'utente
            user_category = None
            if user.category_id:
                user_category = session.get(Category, user.category_id)
                logger.info(f"User category: {user_category.name if user_category else 'None'}")
            
            # Converti aree_interesse da stringa a lista
            aree_interesse_list = user.aree_interesse.split(',') if user.aree_interesse else []
            
            return templates.TemplateResponse("profile.html", {
                "request": request,
                "user": user,
                "categories": categories,
                "user_category": user_category,
                "aree_interesse_list": aree_interesse_list
            })
    except Exception as e:
        logger.error(f"Error in profile: {e}", exc_info=True)
        return RedirectResponse("/login")

@router.post("/api/update-profile")
def update_profile(
    request: Request,
    nome: Optional[str] = Form(None),
    professione: Optional[str] = Form(None),
    descrizione: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    aree_interesse: Optional[str] = Form(None),
    prezzo_consulenza: Optional[int] = Form(None),
    durata_consulenza: Optional[int] = Form(None)
):
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    try:
        payload = verify_token(session_token)
        user_id = payload.get("user_id")
        
        if not user_id:
            return JSONResponse({"error": "Invalid token"}, status_code=401)
        
        # 🔥 USA WITH
        with get_session() as session:
            user = session.get(User, user_id)
            if not user:
                return JSONResponse({"error": "User not found"}, status_code=404)
            
            if nome is not None:
                user.nome = nome
            if professione is not None:
                user.professione = professione
            if descrizione is not None:
                user.descrizione = descrizione
            if category_id is not None:
                user.category_id = category_id if category_id > 0 else None
                logger.info(f"Updated category_id to: {user.category_id}")
            if aree_interesse is not None:
                user.aree_interesse = aree_interesse
            if prezzo_consulenza is not None:
                user.prezzo_consulenza = prezzo_consulenza
            if durata_consulenza is not None:
                user.durata_consulenza = durata_consulenza
            
            session.add(user)
            session.commit()
            session.refresh(user)
            
            logger.info(f"Profile updated for user: {user.email}, category_id: {user.category_id}")
            
            return JSONResponse({"message": "Profile updated successfully"}, status_code=200)
    except Exception as e:
        logger.error(f"Error updating profile: {e}", exc_info=True)
        return JSONResponse({"error": "Failed to update profile"}, status_code=500)

@router.post("/api/upload-profile-picture")
async def upload_profile_picture(
    request: Request,
    file: UploadFile = File(...)
):
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    try:
        payload = verify_token(session_token)
        user_id = payload.get("user_id")
        
        if not user_id:
            return JSONResponse({"error": "Invalid token"}, status_code=401)
        
        # Verifica che sia un'immagine
        if not file.content_type.startswith('image/'):
            return JSONResponse({"error": "File must be an image"}, status_code=400)
        
        # Crea la cartella uploads se non esiste
        upload_dir = Path("app/static/uploads/profile_pictures")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Genera nome file unico
        file_extension = file.filename.split('.')[-1]
        unique_filename = f"{user_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
        file_path = upload_dir / unique_filename
        
        # Salva il file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Aggiorna il database
        with get_session() as session:
            user = session.get(User, user_id)
            if not user:
                return JSONResponse({"error": "User not found"}, status_code=404)
            
            # Elimina la vecchia immagine se esiste
            if user.profile_picture:
                old_file = Path(f"app/static{user.profile_picture}")
                if old_file.exists():
                    old_file.unlink()
            
            # Salva il nuovo percorso (relativo a /static/)
            user.profile_picture = f"/uploads/profile_pictures/{unique_filename}"
            session.add(user)
            session.commit()
            
            logger.info(f"Profile picture uploaded for user {user.email}: {unique_filename}")
            
            return JSONResponse({
                "message": "Profile picture uploaded successfully",
                "url": user.profile_picture
            })
    
    except Exception as e:
        logger.error(f"Error uploading profile picture: {e}", exc_info=True)
        return JSONResponse({"error": "Failed to upload image"}, status_code=500)