from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.models import User, Category, CategoryHierarchy
from app.database import get_session
from app.logger_config import logger
from app.utils.template_helpers import get_all_categories
from sqlmodel import select
import json

router = APIRouter()

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
        
        # Carica le sottocategorie selezionate dall'utente
        subcategories = []
        if user.selected_subcategories:
            try:
                sub_ids = json.loads(user.selected_subcategories)
                sub_ids_int = [int(sid) for sid in sub_ids]
                for sid in sub_ids_int:
                    sub_cat = session.get(Category, sid)
                    if sub_cat:
                        subcategories.append(sub_cat)
            except (json.JSONDecodeError, ValueError):
                pass
        
        # Converti aree_interesse da stringa a lista
        aree_interesse_list = user.aree_interesse.split(',') if user.aree_interesse else []
        
        # Ottieni l'utente loggato (se c'è) - USA verify_token con Request
        current_user = None
        try:
            from app.routes.auth import verify_token
            current_user = verify_token(request)
        except:
            pass
        
        # Carica tutte le categorie principali per il dropdown nel navbar
        categories = get_all_categories()
        
        logger.info(f"Public profile viewed: {user.email} (ID: {user.id}) by {current_user.email if current_user else 'anonymous'}")
        
        return request.app.state.templates.TemplateResponse("user_profile.html", {
            "request": request,
            "user": user,  # Utente del profilo che stai visualizzando
            "current_user": current_user,  # Utente loggato
            "category": category,
            "aree_interesse_list": aree_interesse_list,
            "subcategories": subcategories,
            "is_own_profile": current_user and current_user.id == user.id,
            "categories": categories
        })