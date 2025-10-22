from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.models_user import User
from app.models_category import Category
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
        
        # Converti aree_interesse da stringa a lista (rimuovi macro_aree)
        aree_interesse_list = user.aree_interesse.split(',') if user.aree_interesse else []
        
        # Ottieni l'utente loggato (se c'è)
        current_user = None
        session_token = request.cookies.get("session_token")
        if session_token:
            try:
                from app.auth import verify_token
                payload = verify_token(session_token)
                current_user_id = payload.get("user_id")
                if current_user_id:
                    current_user = session.get(User, current_user_id)
            except:
                pass
        
        logger.info(f"Public profile viewed: {user.email} (ID: {user.id})")
        
        return templates.TemplateResponse("public_profile.html", {
            "request": request,
            "user": user,
            "current_user": current_user,
            "category": category,
            "aree_interesse_list": aree_interesse_list,
            "is_own_profile": current_user and current_user.id == user.id
        })