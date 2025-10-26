from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from app.database import get_session
from app.models import User, Category
from sqlmodel import select, col
from app.logger_config import logger
from app.routes.auth import verify_token
from typing import Optional
import math

router = APIRouter()

@router.get("/consultants", response_class=HTMLResponse)
async def consultants_page(
    request: Request,
    category: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    min_price: Optional[int] = Query(None),
    max_price: Optional[int] = Query(None),
    page: int = Query(1, ge=1)
):
    """Pagina lista consulenti con filtri e paginazione"""
    
    # Verifica utente corrente (se loggato)
    current_user = verify_token(request)
    
    with get_session() as session:
        # Query base: solo utenti confermati
        query = select(User).where(User.confirmed == 1)
        
        # Filtro categoria
        if category:
            query = query.where(User.category_id == category)
        
        # Filtro ricerca (nome, cognome, professione, descrizione)
        if search:
            search_term = f"%{search}%"
            query = query.where(
                (User.nome.ilike(search_term)) |
                (User.cognome.ilike(search_term)) |
                (User.professione.ilike(search_term)) |
                (User.descrizione.ilike(search_term))
            )
        
        # Filtro prezzo
        if min_price is not None:
            query = query.where(User.prezzo_consulenza >= min_price)
        
        if max_price is not None:
            query = query.where(User.prezzo_consulenza <= max_price)
        
        # Conta totale risultati
        total_count = len(session.exec(query).all())
        
        # Paginazione
        items_per_page = 12
        total_pages = math.ceil(total_count / items_per_page) if total_count > 0 else 1
        offset = (page - 1) * items_per_page
        
        # Applica paginazione alla query
        consultants = session.exec(
            query.offset(offset).limit(items_per_page)
        ).all()
        
        # Carica tutte le categorie per la sidebar
        categories = session.exec(select(Category)).all()
        
        logger.info(f"✅ Loaded {len(consultants)} consultants (page {page}/{total_pages}, total: {total_count})")
        
        return request.app.state.templates.TemplateResponse(
            "consultants.html",
            {
                "request": request,
                "consultants": consultants,
                "categories": categories,
                "user": current_user,  # Per navbar
                "selected_category": category,
                "search_query": search or "",
                "min_price": min_price,
                "max_price": max_price,
                "current_page": page,
                "total_pages": total_pages,
                "total_count": total_count
            }
        )

@router.get("/user/{user_id}", response_class=HTMLResponse)
async def public_user_profile(request: Request, user_id: int):
    """Profilo pubblico di un consulente"""
    try:
        current_user = verify_token(request)
        
        with get_session() as session:
            user = session.get(User, user_id)
            
            if not user:
                logger.warning(f"❌ User ID {user_id} not found")
                raise HTTPException(status_code=404, detail="Utente non trovato")
            
            if user.confirmed != 1:
                logger.warning(f"❌ User ID {user_id} not confirmed")
                raise HTTPException(status_code=404, detail="Profilo non disponibile")
            
            # Carica categoria
            category = None
            if user.category_id:
                category = session.get(Category, user.category_id)
            
            is_own_profile = current_user and current_user.id == user.id
            
            # Prepara dati utente
            user_data = {
                "id": user.id,
                "email": user.email,
                "nome": user.nome or "",
                "cognome": user.cognome or "",
                "professione": user.professione or "",
                "descrizione": user.descrizione or "",
                "profile_picture": user.profile_picture or "/static/default-avatar.png",
                "category_id": user.category_id,
                "aree_interesse": user.aree_interesse or "",
                "prezzo_consulenza": user.prezzo_consulenza or 150,
                "durata_consulenza": getattr(user, 'durata_consulenza', 60),
                "bollini": user.bollini or 0,
                "consulenze_vendute": user.consulenze_vendute or 0,
                "consulenze_acquistate": user.consulenze_acquistate or 0,
                "confirmed": user.confirmed,
                "created_at": user.created_at.strftime("%Y-%m-%d") if user.created_at else "N/A"
            }
            
            # Split aree interesse
            aree_interesse_list = []
            if user.aree_interesse:
                aree_interesse_list = [a.strip() for a in user.aree_interesse.split(',')]
            
            # Macro aree (se esiste)
            macro_aree_list = []
            if hasattr(user, 'macro_aree') and user.macro_aree:
                macro_aree_list = [a.strip() for a in user.macro_aree.split(',')]
            
            logger.info(f"✅ Loaded public profile: {user.email} (viewed by: {current_user.email if current_user else 'guest'})")
            
            return request.app.state.templates.TemplateResponse(
                "user_profile.html",
                {
                    "request": request,
                    "user": user_data,
                    "category": category,
                    "current_user": current_user,
                    "is_own_profile": is_own_profile,
                    "aree_interesse_list": aree_interesse_list,
                    "macro_aree_list": macro_aree_list
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading user profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Errore interno")

@router.get("/api/consultants", response_class=JSONResponse)
async def api_consultants(
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None
):
    """API per filtrare consulenti"""
    try:
        with get_session() as session:
            query = select(User).where(User.confirmed == 1)
            
            if category_id:
                query = query.where(User.category_id == category_id)
            
            if search:
                search_term = f"%{search}%"
                query = query.where(
                    (User.nome.ilike(search_term)) |
                    (User.cognome.ilike(search_term)) |
                    (User.professione.ilike(search_term))
                )
            
            if min_price is not None:
                query = query.where(User.prezzo_consulenza >= min_price)
            
            if max_price is not None:
                query = query.where(User.prezzo_consulenza <= max_price)
            
            consultants = session.exec(query).all()
            
            return JSONResponse({
                "consultants": [
                    {
                        "id": c.id,
                        "nome": c.nome,
                        "cognome": c.cognome,
                        "professione": c.professione,
                        "descrizione": c.descrizione,
                        "profile_picture": c.profile_picture or "/static/default-avatar.png",
                        "prezzo_consulenza": c.prezzo_consulenza,
                        "category_id": c.category_id,
                        "bollini": c.bollini
                    }
                    for c in consultants
                ]
            })
    
    except Exception as e:
        logger.error(f"Error in API consultants: {e}", exc_info=True)
        return JSONResponse({"error": "Errore interno"}, status_code=500)