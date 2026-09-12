from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.database import get_session
from app.models import User, Category, Review
from app.routes.auth import verify_token
from sqlmodel import select, func
from app.logger_config import logger

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Homepage con consulenti in evidenza"""
    
    # Controlla se utente è loggato
    current_user = verify_token(request)
    
    # Categorie disponibili tramite middleware
    categories = getattr(request.state, 'categories', [])
    
    with get_session() as session:
        try:
            # Carica consulenti featured
            featured_consultants_query = (
                select(User)
                .where(User.consulenze_vendute > 0)
                .order_by(User.consulenze_vendute.desc())
                .limit(4)
            )
            # Chi ha fatto accesso non si vede fra i consulenti in evidenza
            if current_user:
                featured_consultants_query = featured_consultants_query.where(User.id != current_user.id)
            featured_users = session.exec(featured_consultants_query).all()
            
            # ✅ Crea struttura dati come nel template (con categoria)
            consultants = []
            for user in featured_users:
                category = None
                if user.category_id:
                    category = session.get(Category, user.category_id)

                # Rating medio dalle recensioni ricevute
                reviews = session.exec(
                    select(Review).where(Review.consultant_user_id == user.id)
                ).all()
                review_count = len(reviews)
                avg_rating = None
                if reviews:
                    total = sum(
                        (r.rating_helpful + r.rating_prepared + r.rating_communication) / 3
                        for r in reviews
                    )
                    avg_rating = round(total / review_count, 1)

                consultants.append({
                    "user": user,
                    "category": category,
                    "avg_rating": avg_rating,
                    "review_count": review_count,
                })
            
            logger.info(f"Home page loaded with {len(consultants)} featured consultants")
            
            return request.app.state.templates.TemplateResponse(
                "home.html",
                {
                    "request": request,
                    "categories": categories,
                    "consultants": consultants,
                    "user": current_user,
                    "current_user": current_user,
                    "hero_img_url": "https://i.imgur.com/YourImage.png"
                }
            )
        except Exception as e:
            logger.error(f"Error loading home page: {e}", exc_info=True)
            
            return request.app.state.templates.TemplateResponse(
                "home.html",
                {
                    "request": request,
                    "categories": [],
                    "consultants": [],
                    "user": current_user,
                    "current_user": current_user,
                    "error": "Errore nel caricamento della pagina"
                }
            )
