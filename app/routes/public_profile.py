from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.models import User
from app.models import Category
from app.database import get_session
from app.logger_config import logger

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/user/{user_id}", response_class=HTMLResponse)
def public_user_profile(request: Request, user_id: int):
    """Visualizza il profilo pubblico di un utente"""
    with get_session() as session:
        user = session.get(User, user_id)
        if not user:
            return RedirectResponse("/")
        
        # Carica la categoria
        category = None
        if user.category_id:
            category = session.get(Category, user.category_id)
        
        # Converti aree_interesse da stringa a lista
        aree_interesse_list = user.aree_interesse.split(',') if user.aree_interesse else []
        
        # Ottieni l'utente loggato (se c'è) - USA verify_token con Request
        current_user = None
        try:
            from app.routes.auth import verify_token
            current_user = verify_token(request)
        except:
            pass
        
        logger.info(f"Public profile viewed: {user.email} (ID: {user.id}) by {current_user.email if current_user else 'anonymous'}")
        
        return templates.TemplateResponse("user_profile.html", {
            "request": request,
            "user": user,  # Utente del profilo che stai visualizzando
            "current_user": current_user,  # Utente loggato
            "category": category,
            "aree_interesse_list": aree_interesse_list,
            "is_own_profile": current_user and current_user.id == user.id
        })