from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from app.models import User, Category
from app.database import get_session
from app.logger_config import logger
from app.routes.auth import verify_token, get_current_user  # ✅ Import da auth.py
from typing import Optional
import uuid
from pathlib import Path
from sqlmodel import select

router = APIRouter()

# ✅ MODIFICA QUESTA ROUTE (aggiungi controllo manuale)
@router.get("/profile", response_class=HTMLResponse)
async def user_profile(request: Request):
    """Profilo privato dell'utente loggato"""
    
    # ✅ AGGIUNGI QUESTO: Controlla autenticazione manualmente
    user = verify_token(request)
    
    # ✅ AGGIUNGI QUESTO: Se non loggato, redirect a /login
    if not user:
        logger.warning("User not authenticated, redirecting to login")
        return RedirectResponse("/login", status_code=302)
    
    # ✅ Resto del codice rimane uguale
    try:
        with get_session() as session:
            # Refresh user da DB
            user = session.get(User, user.id)
            
            if not user:
                logger.warning(f"User {user.id} not found in database")
                return RedirectResponse("/login")
            
            # Carica categorie
            categories = session.exec(select(Category)).all()
            logger.info(f"✅ Loaded {len(categories)} categories")
            
            # Categoria utente
            user_category = None
            if user.category_id:
                user_category = session.get(Category, user.category_id)
            
            # Aree interesse
            aree_interesse_list = user.aree_interesse.split(',') if user.aree_interesse else []
            
            return request.app.state.templates.TemplateResponse(
                "profile.html",
                {
                    "request": request,
                    "user": user,
                    "categories": categories,
                    "user_category": user_category,
                    "aree_interesse_list": aree_interesse_list
                }
            )
    except Exception as e:
        logger.error(f"Error in profile: {e}", exc_info=True)
        return RedirectResponse("/login")

@router.post("/api/update-profile")
async def update_profile(
    request: Request,
    current_user: User = Depends(get_current_user),  # ✅ USA DEPENDENCY
    nome: Optional[str] = Form(None),
    professione: Optional[str] = Form(None),
    descrizione: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    aree_interesse: Optional[str] = Form(None),
    prezzo_consulenza: Optional[int] = Form(None),
    durata_consulenza: Optional[int] = Form(None)
):
    """Aggiorna profilo utente"""
    try:
        with get_session() as session:
            user = session.get(User, current_user.id)
            
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
            if aree_interesse is not None:
                user.aree_interesse = aree_interesse
            if prezzo_consulenza is not None:
                user.prezzo_consulenza = prezzo_consulenza
            if durata_consulenza is not None:
                user.durata_consulenza = durata_consulenza
            
            session.add(user)
            session.commit()
            
            logger.info(f"Profile updated for user: {user.email}")
            
            return JSONResponse({"message": "Profile updated successfully"}, status_code=200)
    except Exception as e:
        logger.error(f"Error updating profile: {e}", exc_info=True)
        return JSONResponse({"error": "Failed to update profile"}, status_code=500)

@router.post("/api/upload-profile-picture")
async def upload_profile_picture(
    request: Request,
    current_user: User = Depends(get_current_user),  # ✅ USA DEPENDENCY
    file: UploadFile = File(...)
):
    """Upload immagine profilo"""
    try:
        if not file.content_type.startswith('image/'):
            return JSONResponse({"error": "File must be an image"}, status_code=400)
        
        upload_dir = Path("app/static/uploads/profile_pictures")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_extension = file.filename.split('.')[-1]
        unique_filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}.{file_extension}"
        file_path = upload_dir / unique_filename
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        with get_session() as session:
            user = session.get(User, current_user.id)
            
            if not user:
                return JSONResponse({"error": "User not found"}, status_code=404)
            
            # Elimina vecchia immagine
            if user.profile_picture:
                old_file = Path(f"app/static{user.profile_picture}")
                if old_file.exists():
                    old_file.unlink()
            
            user.profile_picture = f"/uploads/profile_pictures/{unique_filename}"
            session.add(user)
            session.commit()
            
            logger.info(f"Profile picture uploaded: {unique_filename}")
            
            return JSONResponse({
                "message": "Profile picture uploaded successfully",
                "url": user.profile_picture
            })
    
    except Exception as e:
        logger.error(f"Error uploading profile picture: {e}", exc_info=True)
        return JSONResponse({"error": "Failed to upload image"}, status_code=500)

@router.get("/user/{user_id}", response_class=HTMLResponse)
async def view_user_profile(user_id: int, request: Request):
    """Profilo pubblico di un utente"""
    
    # ✅ AGGIUNGI: Controlla se utente è loggato
    current_user = verify_token(request)
    
    with get_session() as session:
        user = session.get(User, user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="Utente non trovato")
        
        # Carica categoria dell'utente
        category = None
        if user.category_id:
            category = session.get(Category, user.category_id)
        
        return request.app.state.templates.TemplateResponse(
            "user_profile.html",
            {
                "request": request,
                "profile_user": user,  # Utente del profilo visualizzato
                "category": category,
                "user": current_user  # ✅ Utente loggato (per navbar)
            }
        )