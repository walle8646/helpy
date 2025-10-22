from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from app.models import ImageLink
from app.models_user import User
from app.models_category import Category
from app.database import get_session
from app.logger_config import logger

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    with get_session() as session:
        # Carica le immagini esistenti
        images = session.exec(select(ImageLink)).all()
        image_dict = {img.name: img.url for img in images}
        
        # Carica 4 consulenti featured (con più consulenze vendute)
        featured_consultants = session.exec(
            select(User)
            .where(User.confirmed == 1)
            .where(User.nome.isnot(None))
            .order_by(User.consulenze_vendute.desc())
            .limit(4)
        ).all()
        
        # Carica le categorie per ogni consulente
        consultants_with_category = []
        for consultant in featured_consultants:
            category = None
            if consultant.category_id:
                category = session.get(Category, consultant.category_id)
            consultants_with_category.append({
                'user': consultant,
                'category': category
            })
        
        # Ottieni l'utente loggato (se c'è)
        current_user = None
        session_token = request.cookies.get("session_token")
        if session_token:
            try:
                from app.auth import verify_token
                payload = verify_token(session_token)
                user_id = payload.get("user_id")
                if user_id:
                    current_user = session.get(User, user_id)
            except:
                pass
        
        logger.info(f"Home page loaded with {len(featured_consultants)} featured consultants")
        
        return templates.TemplateResponse("home.html", {
            "request": request,
            "title": "Helpy - Connect with Experts",
            "user": current_user,
            "hero_img_url": image_dict.get("hero", "https://i.imgur.com/XGQYrXm.png"),
            "consultants": consultants_with_category
        })
