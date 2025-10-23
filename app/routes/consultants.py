from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select, or_, and_
from app.models_user import User
from app.models_category import Category
from app.database import get_session
from app.logger_config import logger
from typing import Optional
import re

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# 🔥 Dizionario di parole correlate per ricerca intelligente
SEARCH_KEYWORDS = {
    # Finanza e Business
    "finanziamenti": ["finanza", "prestiti", "credito", "banca", "investimenti", "capitale", "fundraising", "business plan", "startup"],
    "soldi": ["finanza", "investimenti", "risparmio", "budget", "trading", "crypto", "denaro"],
    "investimenti": ["finanza", "azioni", "trading", "crypto", "portafoglio", "rendite", "immobili"],
    "startup": ["business", "imprenditoria", "fundraising", "pitch", "innovazione"],
    
    # Lavoro e Carriera
    "lavoro": ["carriera", "cv", "colloqui", "linkedin", "recruiting", "hr"],
    "cv": ["curriculum", "resume", "lettera motivazionale", "career"],
    "colloquio": ["intervista", "recruiting", "selezione", "hr"],
    "cambio lavoro": ["career", "transizione", "orientamento"],
    
    # Marketing e Digital
    "marketing": ["seo", "ads", "social media", "instagram", "facebook", "google", "pubblicità"],
    "social": ["instagram", "tiktok", "facebook", "social media", "content"],
    "seo": ["google", "posizionamento", "traffico", "blog", "content"],
    "vendere online": ["e-commerce", "shopify", "amazon", "dropshipping"],
    
    # Tech e Programmazione
    "programmazione": ["coding", "developer", "software", "python", "javascript", "web"],
    "sito web": ["wordpress", "web design", "frontend", "html", "css"],
    "app": ["mobile", "ios", "android", "react native", "flutter"],
    
    # Design e Creatività
    "design": ["grafica", "logo", "branding", "ui", "ux", "figma"],
    "logo": ["branding", "brand identity", "grafica"],
    
    # Benessere
    "dieta": ["nutrizione", "alimentazione", "perdere peso", "meal prep"],
    "fitness": ["allenamento", "palestra", "personal trainer", "workout"],
    "stress": ["mindfulness", "benessere", "psicologia", "yoga"],
    
    # Estero
    "estero": ["expat", "trasferimento", "visto", "emigrare", "remote work"],
    "visto": ["immigrazione", "cittadinanza", "permesso", "relocation"],
}

def expand_search_query(query: str) -> list:
    """
    Espande la query di ricerca con parole correlate
    """
    query_lower = query.lower().strip()
    expanded_terms = [query_lower]
    
    # Cerca parole chiave correlate
    for keyword, related_terms in SEARCH_KEYWORDS.items():
        if keyword in query_lower or query_lower in keyword:
            expanded_terms.extend(related_terms)
    
    # Rimuovi duplicati
    return list(set(expanded_terms))

@router.get("/consultants", response_class=HTMLResponse)
def consultants_page(
    request: Request,
    category: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    min_price: Optional[int] = Query(None),
    max_price: Optional[int] = Query(None),
    page: int = Query(1, ge=1)
):
    per_page = 12
    offset = (page - 1) * per_page
    
    with get_session() as session:
        # Carica tutte le categorie per i filtri
        categories = session.exec(select(Category)).all()
        
        # Query base: solo utenti confermati con nome
        query = select(User).where(
            and_(
                User.confirmed == 1,
                User.nome.isnot(None)
            )
        )
        
        # Filtro per categoria
        if category:
            query = query.where(User.category_id == category)
        
        # 🔥 RICERCA INTELLIGENTE con termini espansi
        if search:
            # Espandi la query con termini correlati
            expanded_terms = expand_search_query(search)
            
            # Crea condizioni OR per tutti i termini
            search_conditions = []
            for term in expanded_terms:
                term_pattern = f"%{term}%"
                search_conditions.append(User.nome.like(term_pattern))
                search_conditions.append(User.professione.like(term_pattern))
                search_conditions.append(User.descrizione.like(term_pattern))
                search_conditions.append(User.aree_interesse.like(term_pattern))
            
            # Applica tutte le condizioni con OR
            if search_conditions:
                query = query.where(or_(*search_conditions))
            
            logger.info(f"Ricerca: '{search}' → Termini espansi: {expanded_terms}")
        
        # Filtro per range di prezzo
        if min_price is not None and min_price >= 10:
            query = query.where(User.prezzo_consulenza >= min_price)
        
        if max_price is not None and max_price >= 10:
            query = query.where(User.prezzo_consulenza <= max_price)
        
        # Ordina per rilevanza (bollini e consulenze vendute)
        query = query.order_by(User.bollini.desc(), User.consulenze_vendute.desc())
        
        # Conta totale per paginazione
        total_count = len(session.exec(query).all())
        total_pages = (total_count + per_page - 1) // per_page
        
        # Applica paginazione
        consultants = session.exec(query.limit(per_page).offset(offset)).all()
        
        # Carica le categorie per ogni consulente
        consultants_with_category = []
        for consultant in consultants:
            category_obj = None
            if consultant.category_id:
                category_obj = session.get(Category, consultant.category_id)
            consultants_with_category.append({
                "user": consultant,
                "category": category_obj
            })
        
        response = templates.TemplateResponse("consultants.html", {
            "request": request,
            "consultants": consultants_with_category,
            "categories": categories,
            "selected_category": category,
            "search_query": search or "",
            "min_price": min_price,
            "max_price": max_price,
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count
        })
        
        # Aggiungi intestazioni per il caching
        response.headers["Cache-Control"] = "public, max-age=3600"  # Cache per 1 ora
        response.headers["Expires"] = "Wed, 21 Oct 2025 07:28:00 GMT"
        
        logger.info(f"Filtri applicati - Category: {category}, Search: {search}, Min: {min_price}, Max: {max_price}")
        
        return response