from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.database import get_session
from app.models import User, Category
from app.routes.auth import verify_token
from sqlmodel import select, func
from app.logger_config import logger

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Homepage con consulenti in evidenza"""
    
    # Controlla se utente è loggato
    current_user = verify_token(request)
    
    with get_session() as session:
        try:
            # Carica categorie
            categories = session.exec(select(Category)).all()
            
            # Carica consulenti featured (con bollini > 0)
            featured_consultants_query = (
                select(User)
                .where(User.bollini > 0)
                .order_by(User.bollini.desc())
                .limit(4)
            )
            featured_users = session.exec(featured_consultants_query).all()
            
            # ✅ Crea struttura dati come nel template (con categoria)
            consultants = []
            for user in featured_users:
                category = None
                if user.category_id:
                    category = session.get(Category, user.category_id)
                
                consultants.append({
                    "user": user,
                    "category": category
                })
            
            logger.info(f"Home page loaded with {len(consultants)} featured consultants")
            
            return request.app.state.templates.TemplateResponse(
                "home.html",
                {
                    "request": request,
                    "categories": categories,
                    "consultants": consultants,  # ✅ Nome corretto
                    "user": current_user,  # ✅ Rinominato da current_user a user
                    "hero_img_url": "https://i.imgur.com/YourImage.png"  # Opzionale
                }
            )
        except Exception as e:
            logger.error(f"Error loading home page: {e}", exc_info=True)
            
            return request.app.state.templates.TemplateResponse(
                "home.html",
                {
                    "request": request,
                    "categories": [],
                    "consultants": [],  # ✅ Nome corretto
                    "user": current_user,  # ✅ Rinominato
                    "error": "Errore nel caricamento della pagina"
                }
            )
