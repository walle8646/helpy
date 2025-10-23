from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from app.database import get_session
from app.models import User, Category
from app.routes.auth import verify_token  # ✅ DEVE ESSERE IMPORTATO
from sqlmodel import select, or_, func
from typing import Optional
from app.logger_config import logger
import math

router = APIRouter()

@router.get("/consultants", response_class=HTMLResponse)
async def list_consultants(
    request: Request,
    category: Optional[int] = Query(None, alias="category"),
    search: Optional[str] = Query(None),
    min_price: Optional[int] = Query(None),
    max_price: Optional[int] = Query(None),
    page: int = Query(1, ge=1)
):
    """Pagina lista consulenti con filtri"""
    
    # ✅ AGGIUNGI QUESTO (controlla se è presente)
    current_user = verify_token(request)
    
    # ✅ AGGIUNGI QUESTO LOG TEMPORANEO
    if current_user:
        logger.info(f"✅ User logged: {current_user.email} (ID: {current_user.id})")
    else:
        logger.warning("⚠️ No user logged in")
    
    with get_session() as session:
        try:
            # Query base
            query = select(User).where(User.bollini > 0)
            
            # Filtro categoria
            if category:
                query = query.where(User.category_id == category)
            
            # Filtro ricerca
            if search:
                search_term = f"%{search}%"
                query = query.where(
                    or_(
                        User.nome.ilike(search_term),
                        User.professione.ilike(search_term),
                        User.descrizione.ilike(search_term)
                    )
                )
            
            # Filtro prezzo
            if min_price is not None:
                query = query.where(User.prezzo_consulenza >= min_price)
            if max_price is not None:
                query = query.where(User.prezzo_consulenza <= max_price)
            
            # Conta totale
            count_query = select(func.count()).select_from(query.subquery())
            total_count = session.exec(count_query).one()
            
            # Paginazione
            per_page = 12
            total_pages = math.ceil(total_count / per_page)
            offset = (page - 1) * per_page
            
            query = query.order_by(User.bollini.desc()).limit(per_page).offset(offset)
            
            consultants_list = session.exec(query).all()
            
            # Carica categorie
            consultants = []
            for user in consultants_list:
                cat = None
                if user.category_id:
                    cat = session.get(Category, user.category_id)
                
                consultants.append({
                    "user": user,
                    "category": cat
                })
            
            categories = session.exec(select(Category)).all()
            
            logger.info(f"Consultants page loaded: {len(consultants)} results")
            
            # ✅ VERIFICA CHE `user` SIA PASSATO QUI
            return request.app.state.templates.TemplateResponse(
                "consultants.html",
                {
                    "request": request,
                    "consultants": consultants,
                    "categories": categories,
                    "selected_category": category,
                    "search_query": search or "",
                    "min_price": min_price,
                    "max_price": max_price,
                    "total_count": total_count,
                    "current_page": page,
                    "total_pages": total_pages,
                    "user": current_user  # ✅ DEVE ESSERE PRESENTE
                }
            )
        
        except Exception as e:
            logger.error(f"Error loading consultants: {e}", exc_info=True)
            
            return request.app.state.templates.TemplateResponse(
                "consultants.html",
                {
                    "request": request,
                    "consultants": [],
                    "categories": [],
                    "selected_category": category,
                    "search_query": search or "",
                    "min_price": min_price,
                    "max_price": max_price,
                    "total_count": 0,
                    "current_page": 1,
                    "total_pages": 1,
                    "user": current_user,  # ✅ ANCHE IN CASO DI ERRORE
                    "error": "Errore nel caricamento dei consulenti"
                }
            )

@router.get("/category/{slug}", response_class=HTMLResponse)
async def category_page(slug: str, request: Request):
    """Pagina categoria specifica"""
    
    # ✅ AGGIUNGI: Controlla se utente è loggato
    current_user = verify_token(request)
    
    with get_session() as session:
        # Trova categoria
        category = session.exec(select(Category).where(Category.slug == slug)).first()
        
        if not category:
            return request.app.state.templates.TemplateResponse(
                "error.html",
                {
                    "request": request,
                    "error": "Categoria non trovata",
                    "user": current_user  # ✅ Passa utente
                },
                status_code=404
            )
        
        # Carica consulenti della categoria
        consultants_query = (
            select(User)
            .where(User.category_id == category.id)
            .where(User.bollini > 0)
            .order_by(User.bollini.desc())
        )
        consultants_list = session.exec(consultants_query).all()
        
        # Aggiungi categoria a ogni consulente
        consultants = []
        for user in consultants_list:
            consultants.append({
                "user": user,
                "category": category
            })
        
        return request.app.state.templates.TemplateResponse(
            "category.html",
            {
                "request": request,
                "category": category,
                "consultants": consultants,
                "user": current_user  # ✅ Passa utente loggato
            }
        )