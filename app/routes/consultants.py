from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from sqlmodel import select, or_, and_, func
from typing import Optional
import re

from app.database import get_session
from app.models import User, Category, CategoryHierarchy, Review
from app.routes.auth import verify_token
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
        user.aree_interesse or '',  # ✅ Rimosso macro_aree
        user.tags or ''  # 🏷️ Tags generati da AI
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
    min_rating: Optional[float] = Query(None),
    page: int = Query(1, ge=1)
):
    """Pagina consulenti con filtri avanzati e ricerca intelligente"""
    
    try:
        # ✅ Verifica utente loggato
        current_user = verify_token(request)
        
        with get_session() as session:
            # ========== CARICA CATEGORIE PRINCIPALI ==========
            principal_categories = session.exec(
                select(Category).where(Category.is_principal == True).order_by(Category.id)
            ).all()
            
            # ========== COSTRUISCI STRUTTURA CATEGORIE CON SOTTOCATEGORIE ==========
            categories_with_children = []
            child_to_parent_map = {}  # Mappa: child_id -> parent_id
            
            for parent_cat in principal_categories:
                # Carica le sottocategorie di questa categoria
                hierarchy_entries = session.exec(
                    select(CategoryHierarchy)
                    .where(CategoryHierarchy.parent_category_id == parent_cat.id)
                    .order_by(CategoryHierarchy.position)
                ).all()
                
                # Carica i dati completi delle sottocategorie
                children = []
                for hierarchy in hierarchy_entries:
                    child_cat = session.get(Category, hierarchy.child_category_id)
                    if child_cat:
                        children.append(child_cat)
                        # Popola la mappa
                        child_to_parent_map[child_cat.id] = parent_cat.id
                
                categories_with_children.append({
                    'parent': parent_cat,
                    'children': children
                })
            
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
                                ),
                                and_(
                                    User.tags.isnot(None),
                                    User.tags.ilike(keyword_pattern)
                                )
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
            
            # ========== FILTRO PER RECENSIONI ==========
            if min_rating is not None and min_rating > 0:
                # Carica review stats per tutti i risultati e filtra
                all_ids = [u.id for u in consultants]
                rating_map = {}
                if all_ids:
                    rating_rows = session.exec(
                        select(
                            Review.consultant_user_id,
                            func.count(Review.id),
                            func.avg(Review.rating_helpful),
                            func.avg(Review.rating_prepared),
                            func.avg(Review.rating_communication),
                        )
                        .where(Review.consultant_user_id.in_(all_ids))
                        .group_by(Review.consultant_user_id)
                    ).all()
                    for row in rating_rows:
                        avg = round((row[2] + row[3] + row[4]) / 3, 1)
                        rating_map[row[0]] = avg
                
                consultants = [
                    u for u in consultants
                    if rating_map.get(u.id, 0) >= min_rating
                ]
            
            total_count = len(consultants)
            
            # ========== PAGINAZIONE ==========
            per_page = 12
            offset = (page - 1) * per_page
            total_pages = max(1, (total_count + per_page - 1) // per_page)
            
            consultants = consultants[offset:offset + per_page]
            
            # ========== ENRICHMENT DATI ==========
            # Carica medie recensioni per tutti i consulenti in una query
            consultant_ids = [u.id for u in consultants]
            review_stats = {}
            if consultant_ids:
                stats_rows = session.exec(
                    select(
                        Review.consultant_user_id,
                        func.count(Review.id),
                        func.avg(Review.rating_helpful),
                        func.avg(Review.rating_prepared),
                        func.avg(Review.rating_communication),
                    )
                    .where(Review.consultant_user_id.in_(consultant_ids))
                    .group_by(Review.consultant_user_id)
                ).all()
                for row in stats_rows:
                    avg = round((row[2] + row[3] + row[4]) / 3, 1)
                    review_stats[row[0]] = {'count': row[1], 'avg': avg}

            enriched_consultants = []
            for user in consultants:
                stats = review_stats.get(user.id, {'count': 0, 'avg': 0})
                user_data = {
                    'id': user.id,
                    'nome': user.nome,
                    'cognome': user.cognome,
                    'professione': user.professione,
                    'descrizione': user.descrizione,
                    'profile_picture': user.profile_picture,
                    'prezzo_consulenza': user.prezzo_consulenza,
                    'review_avg': stats['avg'],
                    'review_count': stats['count'],
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
                    "user": current_user,
                    "current_user": current_user,
                    "consultants": enriched_consultants,
                    "categories": principal_categories,
                    "categories_with_children": categories_with_children,
                    "child_to_parent_map": child_to_parent_map,
                    "selected_category": category,
                    "search_query": search or '',
                    "min_price": min_price,
                    "max_price": max_price,
                    "min_rating": min_rating,
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_count": total_count
                }
            )
    
    except Exception as e:
        logger.error(f"❌ Error loading consultants page: {e}", exc_info=True)
        
        try:
            with get_session() as session:
                principal_categories = session.exec(
                    select(Category).where(Category.is_principal == True).order_by(Category.id)
                ).all()
                categories_with_children = []
                for parent_cat in principal_categories:
                    categories_with_children.append({
                        'parent': parent_cat,
                        'children': []
                    })
        except:
            categories_with_children = []
        
        return request.app.state.templates.TemplateResponse(
            "consultants.html",
            {
                "request": request,
                "user": None,  # ⚠️ Mantenuto per compatibilità
                "current_user": None,  # ✅ Aggiunto per navbar
                "consultants": [],
                "categories": [],
                "categories_with_children": categories_with_children,
                "child_to_parent_map": {},
                "selected_category": None,
                "search_query": '',
                "min_price": None,
                "max_price": None,
                "min_rating": None,
                "current_page": 1,
                "total_pages": 1,
                "total_count": 0
            }
        )