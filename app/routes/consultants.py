from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from sqlmodel import select, or_, and_, func
from typing import Optional
import re

from app.database import get_session
from app.models import User, Category
from loguru import logger

router = APIRouter()

# ========== STOP WORDS ITALIANE ==========
STOP_WORDS = {
    'il', 'lo', 'la', 'i', 'gli', 'le',
    'un', 'uno', 'una',
    'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra',
    'del', 'dello', 'della', 'dei', 'degli', 'delle',
    'al', 'allo', 'alla', 'ai', 'agli', 'alle',
    'dal', 'dallo', 'dalla', 'dai', 'dagli', 'dalle',
    'nel', 'nello', 'nella', 'nei', 'negli', 'nelle',
    'sul', 'sullo', 'sulla', 'sui', 'sugli', 'sulle',
    'col', 'coi', 'cogli', 'con',
    'e', 'o', 'ma', 'però', 'perché', 'come', 'quando', 'dove',
    'che', 'chi', 'cui', 'quale', 'quanto'
}

# ========== SINONIMI E TERMINI CORRELATI (ESPANSO) ==========
SYNONYMS = {
    'logo': ['grafica', 'branding', 'design', 'identità', 'visiva', 'brand', 'immagine', 'marchio'],
    'sito': ['web', 'website', 'online', 'internet', 'digitale', 'landing', 'portale'],
    'marketing': ['pubblicità', 'ads', 'social', 'promozione', 'campagna', 'advertising'],
    'video': ['montaggio', 'editing', 'riprese', 'audiovisivo', 'content', 'multimedia'],
    'foto': ['fotografia', 'fotografo', 'immagini', 'shooting', 'scatti', 'photo'],
    'testi': ['copywriting', 'scrittura', 'contenuti', 'articoli', 'blog', 'redazione'],
    'consulenza': ['coaching', 'mentoring', 'formazione', 'supporto', 'aiuto', 'advisory'],
    'startup': ['impresa', 'business', 'azienda', 'imprenditoria', 'lancio', 'entrepreneurship'],
    'ecommerce': ['negozio', 'shop', 'vendita', 'online', 'commercio', 'store'],
    'app': ['applicazione', 'mobile', 'software', 'sviluppo', 'programmazione', 'coding'],
}

# ========== SKILL/TOOL MAPPING (NUOVO!) ==========
SKILL_CATEGORIES = {
    'logo': ['photoshop', 'illustrator', 'figma', 'canva', 'adobe', 'sketch', 'coreldraw', 'inkscape'],
    'grafica': ['photoshop', 'illustrator', 'indesign', 'figma', 'canva', 'adobe', 'sketch'],
    'design': ['photoshop', 'illustrator', 'figma', 'sketch', 'adobe', 'ux', 'ui'],
    'web': ['html', 'css', 'javascript', 'wordpress', 'webflow', 'wix', 'react', 'vue', 'angular'],
    'sito': ['html', 'css', 'javascript', 'wordpress', 'webflow', 'wix', 'shopify'],
    'video': ['premiere', 'after effects', 'final cut', 'davinci', 'capcut', 'editing'],
    'foto': ['photoshop', 'lightroom', 'camera', 'fotografia', 'photo'],
    'social': ['instagram', 'facebook', 'tiktok', 'linkedin', 'twitter', 'meta'],
    'marketing': ['google ads', 'facebook ads', 'seo', 'sem', 'analytics', 'meta'],
    'app': ['swift', 'kotlin', 'react native', 'flutter', 'ios', 'android'],
}

def expand_with_skills(keywords: list[str]) -> list[str]:
    """
    Espande keywords con skill/tool correlati.
    
    Es: ['logo'] → ['logo', 'photoshop', 'illustrator', 'figma', 'canva', ...]
    """
    expanded = set(keywords)
    
    for keyword in keywords:
        # Aggiungi sinonimi
        if keyword in SYNONYMS:
            expanded.update(SYNONYMS[keyword])
        
        # Aggiungi skill/tool correlati
        if keyword in SKILL_CATEGORIES:
            expanded.update(SKILL_CATEGORIES[keyword])
    
    return list(expanded)

def clean_search_query(query: str) -> list[str]:
    """Pulisce e splitta la query di ricerca."""
    if not query:
        return []
    
    cleaned = re.sub(r'[^\w\s]', ' ', query.lower())
    words = cleaned.split()
    
    keywords = [
        word for word in words 
        if word not in STOP_WORDS and len(word) >= 3
    ]
    
    return keywords

def calculate_relevance_score(user: User, keywords: list[str], expanded_keywords: list[str]) -> float:
    """
    Calcola uno score di rilevanza per l'utente.
    
    Score più alto = match migliore
    """
    score = 0.0
    
    # Concatena tutti i campi testuale dell'utente
    user_text = ' '.join(filter(None, [
        user.nome or '',
        user.cognome or '',
        user.professione or '',
        user.descrizione or '',
        user.aree_interesse or ''  # ✅ Rimosso macro_aree
    ])).lower()
    
    # +10 punti per ogni keyword originale trovata
    for keyword in keywords:
        if keyword in user_text:
            score += 10
    
    # +5 punti per ogni keyword espansa trovata
    for keyword in expanded_keywords:
        if keyword in user_text:
            score += 5
    
    # +3 punti se professione matcha
    if user.professione:
        prof_lower = user.professione.lower()
        for keyword in keywords:
            if keyword in prof_lower:
                score += 3
    
    # +2 punti per bollini (esperienza)
    score += user.bollini * 2
    
    # +1 punto per consulenze vendute
    score += user.consulenze_vendute
    
    return score

@router.get("/consultants", response_class=HTMLResponse)
async def consultants_page(
    request: Request,
    category: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    page: int = Query(1, ge=1)
):
    """Pagina consulenti con filtri avanzati e ricerca intelligente"""
    
    try:
        with get_session() as session:
            # ========== CARICA CATEGORIE ==========
            categories = session.exec(
                select(Category).order_by(Category.name)
            ).all()
            
            # ========== BASE QUERY ==========
            query_stmt = select(User)
            
            # ========== FILTRO CATEGORIA ==========
            if category:
                query_stmt = query_stmt.where(User.category_id == category)
            
            # ========== FILTRO PREZZO ==========
            if min_price is not None and min_price >= 10:
                query_stmt = query_stmt.where(User.prezzo_consulenza >= min_price)
            
            if max_price is not None and max_price >= 10:
                query_stmt = query_stmt.where(User.prezzo_consulenza <= max_price)
            
            # ========== RICERCA INTELLIGENTE CON SKILL MATCHING ==========
            keywords = []
            expanded_keywords = []
            
            if search:
                keywords = clean_search_query(search)
                expanded_keywords = expand_with_skills(keywords)
                
                logger.info(
                    f"🔍 Search: '{search}'\n"
                    f"   Keywords: {keywords}\n"
                    f"   Expanded: {expanded_keywords[:15]}..."  # Primi 15 per brevità
                )
                
                if expanded_keywords:
                    search_conditions = []
                    
                    for keyword in expanded_keywords:
                        keyword_pattern = f"%{keyword}%"
                        
                        search_conditions.append(
                            or_(
                                User.nome.ilike(keyword_pattern),
                                User.cognome.ilike(keyword_pattern),
                                User.professione.ilike(keyword_pattern),
                                User.descrizione.ilike(keyword_pattern),
                                and_(
                                    User.aree_interesse.isnot(None),
                                    User.aree_interesse.ilike(keyword_pattern)
                                )
                                # ✅ Rimosso blocco macro_aree
                            )
                        )
                    
                    query_stmt = query_stmt.where(or_(*search_conditions))
            
            # ========== ESEGUI QUERY (senza paginazione per scoring) ==========
            all_results = session.exec(query_stmt).all()
            
            # ========== SCORING E ORDINAMENTO ==========
            if search and keywords:
                # Calcola score per ogni risultato
                scored_results = [
                    (user, calculate_relevance_score(user, keywords, expanded_keywords))
                    for user in all_results
                ]
                
                # Ordina per score decrescente
                scored_results.sort(key=lambda x: x[1], reverse=True)
                
                # Log top 5 scores
                logger.info("🏆 Top 5 scores:")
                for user, score in scored_results[:5]:
                    logger.info(f"   {user.nome} {user.cognome}: {score:.1f} pts")
                
                # Estrai solo gli utenti ordinati
                consultants = [user for user, _ in scored_results]
            else:
                consultants = all_results
            
            total_count = len(consultants)
            
            # ========== PAGINAZIONE ==========
            per_page = 12
            offset = (page - 1) * per_page
            total_pages = max(1, (total_count + per_page - 1) // per_page)
            
            consultants = consultants[offset:offset + per_page]
            
            # ========== ENRICHMENT DATI ==========
            enriched_consultants = []
            for user in consultants:
                user_data = {
                    'id': user.id,
                    'nome': user.nome,
                    'cognome': user.cognome,
                    'professione': user.professione,
                    'profile_picture': user.profile_picture,
                    'prezzo_consulenza': user.prezzo_consulenza,
                    'bollini': user.bollini,
                    'consulenze_vendute': user.consulenze_vendute,
                    'category': None
                }
                
                if user.category_id:
                    cat = session.get(Category, user.category_id)
                    if cat:
                        user_data['category'] = cat
                
                enriched_consultants.append(user_data)
            
            logger.info(
                f"📊 Results: {total_count} found, page {page}/{total_pages}"
                f"{f', category: {category}' if category else ''}"
                f"{f', search: {search}' if search else ''}"
            )
            
            return request.app.state.templates.TemplateResponse(
                "consultants.html",
                {
                    "request": request,
                    "consultants": enriched_consultants,
                    "categories": categories,
                    "selected_category": category,
                    "search_query": search or '',
                    "min_price": min_price,
                    "max_price": max_price,
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_count": total_count
                }
            )
    
    except Exception as e:
        logger.error(f"❌ Error loading consultants page: {e}", exc_info=True)
        
        try:
            with get_session() as session:
                categories = session.exec(select(Category).order_by(Category.name)).all()
        except:
            categories = []
        
        return request.app.state.templates.TemplateResponse(
            "consultants.html",
            {
                "request": request,
                "consultants": [],
                "categories": categories,
                "selected_category": None,
                "search_query": '',
                "min_price": None,
                "max_price": None,
                "current_page": 1,
                "total_pages": 1,
                "total_count": 0
            }
        )