from fastapi import APIRouter, Request, Form, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel import select, func, or_, and_
from typing import Optional
from datetime import datetime, timedelta
import os

from app.database import get_session
from app.models import User, Category, CommunityQuestion, CommunityLike, CommunityContact, CommunityQuestionFollow, QuestionStatus, CategoryHierarchy
from app.routes.auth import verify_token
from app.utils_user import get_display_name
from loguru import logger

router = APIRouter()

@router.get("/community", response_class=HTMLResponse)
async def community_page(
    request: Request,
    category: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1)
):
    """Pagina Q&A Community"""
    
    try:
        # Verifica utente loggato
        current_user = verify_token(request)
        
        # 🔍 Debug logging
        if current_user:
            logger.info(f"✅ Community - User logged in: {current_user.nome} (ID: {current_user.id})")
        else:
            logger.warning(f"⚠️ Community - No user logged in. Session: {dict(request.session)}")
        
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
            
            # Mantieni anche la lista delle categorie per compatibilità
            categories = principal_categories
            
            # ========== BASE QUERY ==========
            query_stmt = select(CommunityQuestion).where(
                CommunityQuestion.validation == True  # 🆕 Mostra solo domande validate
            ).order_by(
                CommunityQuestion.created_at.desc()
            )
            
            # ========== FILTRO CATEGORIA ==========
            if category:
                # Verifica se la categoria selezionata è principale o subcategoria
                selected_cat = session.get(Category, category)
                if selected_cat and selected_cat.is_principal:
                    # Se è principale, filtra per primary_category_id
                    query_stmt = query_stmt.where(CommunityQuestion.primary_category_id == category)
                else:
                    # Se è subcategoria, filtra per category_id
                    query_stmt = query_stmt.where(CommunityQuestion.category_id == category)
            
            # ========== FILTRO STATUS ==========
            if status and status in ['open', 'in_progress', 'closed']:
                query_stmt = query_stmt.where(CommunityQuestion.status == status)
            
            # ========== RICERCA ==========
            if search:
                search_pattern = f"%{search}%"
                query_stmt = query_stmt.where(
                    or_(
                        CommunityQuestion.title.ilike(search_pattern),
                        CommunityQuestion.description.ilike(search_pattern)
                    )
                )
            
            # ========== COUNT TOTALE ==========
            count_query = select(func.count(CommunityQuestion.id))
            
            if category:
                # Usa la stessa logica di filtro della query principale
                selected_cat = session.get(Category, category)
                if selected_cat and selected_cat.is_principal:
                    count_query = count_query.where(CommunityQuestion.primary_category_id == category)
                else:
                    count_query = count_query.where(CommunityQuestion.category_id == category)
            
            if status:
                count_query = count_query.where(CommunityQuestion.status == status)
            
            if search:
                search_pattern = f"%{search}%"
                count_query = count_query.where(
                    or_(
                        CommunityQuestion.title.ilike(search_pattern),
                        CommunityQuestion.description.ilike(search_pattern)
                    )
                )
            
            total_count = session.exec(count_query).one()
            
            # ========== PAGINAZIONE ==========
            per_page = 10
            offset = (page - 1) * per_page
            total_pages = max(1, (total_count + per_page - 1) // per_page)
            
            query_stmt = query_stmt.offset(offset).limit(per_page)
            
            # ========== ESEGUI QUERY ==========
            questions = session.exec(query_stmt).all()
            
            # ========== CARICA LIKES UTENTE ==========
            # Se l'utente è loggato, carica tutti i suoi like per mostrare quali domande ha già likato
            user_liked_questions = set()
            if current_user:
                user_likes = session.exec(
                    select(CommunityLike.question_id).where(
                        CommunityLike.user_id == current_user.id
                    )
                ).all()
                user_liked_questions = set(user_likes)
            
            # ========== ENRICHMENT DATI ==========
            enriched_questions = []
            
            for question in questions:
                # Carica autore
                author = session.get(User, question.user_id)
                
                # Carica categoria
                cat = None
                if question.category_id:
                    cat = session.get(Category, question.category_id)
                
                # Trova consulenti suggeriti (solo se è la domanda dell'utente loggato)
                suggested_consultants = []
                
                if current_user and question.user_id == current_user.id and question.category_id:
                    # Top 3 consulenti per categoria con più bollini
                    consultants_query = select(User).where(
                        and_(
                            User.category_id == question.category_id,
                            User.id != current_user.id  # Escludi l'autore
                        )
                    ).order_by(
                        User.bollini.desc(),
                        User.consulenze_vendute.desc()
                    ).limit(3)
                    
                    suggested_consultants = session.exec(consultants_query).all()
                
                enriched_questions.append({
                    'question': question,
                    'author': author,
                    'category': cat,
                    'suggested_consultants': suggested_consultants,
                    'is_owner': current_user and question.user_id == current_user.id,
                    'user_liked': question.id in user_liked_questions  # ✅ Indica se l'utente ha già messo like
                })
            
            # ========== STATS ==========
            stats = {
                'total': session.exec(select(func.count(CommunityQuestion.id))).one(),
                'open': session.exec(
                    select(func.count(CommunityQuestion.id))
                    .where(CommunityQuestion.status == QuestionStatus.OPEN)
                ).one(),
                'closed': session.exec(
                    select(func.count(CommunityQuestion.id))
                    .where(CommunityQuestion.status == QuestionStatus.CLOSED)
                ).one()
            }
            
            logger.info(
                f"📊 Community page: {total_count} questions, page {page}/{total_pages}"
                f"{f', category: {category}' if category else ''}"
                f"{f', search: {search}' if search else ''}"
            )
            
            # ========== TOP CONSULTANTS (Filtrati per categoria se selezionata) ==========
            if category:
                # Filtra consulenti che hanno la categoria selezionata come principale o in selected_subcategories
                top_consultants = session.exec(
                    select(User)
                    .where(
                        or_(
                            User.category_id == category,  # Categoria principale
                            User.selected_subcategories.contains(str(category))  # Tra le subcategorie
                        )
                    )
                    .where(User.bollini > 0)
                    .order_by(User.bollini.desc(), User.consulenze_vendute.desc())
                    .limit(4)
                ).all()
            else:
                # Se non c'è categoria selezionata, mostra i migliori di tutte
                top_consultants = session.exec(
                    select(User)
                    .where(User.bollini > 0)
                    .order_by(User.bollini.desc(), User.consulenze_vendute.desc())
                    .limit(4)
                ).all()
            
            # ========== CONTROLLO LIMITE RICHIESTE ==========
            can_create_question = True
            user_questions_count = 0
            
            if current_user:
                # Calcola data di 7 giorni fa
                seven_days_ago = datetime.now() - timedelta(days=7)
                
                logger.info(f"🔍 Checking questions for user {current_user.id} since {seven_days_ago}")
                
                # Recupera le domande dell'utente negli ultimi 7 giorni per debug
                user_recent_questions = session.exec(
                    select(CommunityQuestion)
                    .where(
                        and_(
                            CommunityQuestion.user_id == current_user.id,
                            CommunityQuestion.created_at >= seven_days_ago
                        )
                    )
                ).all()
                
                user_questions_count = len(user_recent_questions)
                
                # Log dettaglio domande
                for q in user_recent_questions:
                    logger.info(f"  📝 Question ID {q.id}: '{q.title}' - Created: {q.created_at}")
                
                # Se ha già fatto 2 o più domande, non può crearne altre
                can_create_question = user_questions_count < 2
                
                logger.info(
                    f"👤 User {current_user.nome} (ID: {current_user.id}) - Questions in last 7 days: {user_questions_count}/2 "
                    f"- Can create: {can_create_question}"
                )
            
            return request.app.state.templates.TemplateResponse(
                "community.html",
                {
                    "request": request,
                    "user": current_user,  # ⚠️ Mantenuto per compatibilità con template community
                    "current_user": current_user,  # ✅ Aggiunto per navbar
                    "questions": enriched_questions,
                    "categories": categories,
                    "categories_with_children": categories_with_children,  # ✅ Per sidebar categorie
                    "child_to_parent_map": child_to_parent_map,  # ✅ Per espandere quando subcategoria selezionata
                    "selected_category": category,
                    "search_query": search or '',
                    "selected_status": status,
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_count": total_count,
                    "stats": stats,
                    "top_consultants": top_consultants,
                    "can_create_question": can_create_question,
                    "user_questions_count": user_questions_count
                }
            )
    
    except Exception as e:
        logger.error(f"❌ Error loading community page: {e}", exc_info=True)
        
        try:
            with get_session() as session:
                categories = session.exec(select(Category).order_by(Category.name)).all()
        except:
            categories = []
        
        return request.app.state.templates.TemplateResponse(
            "community.html",
            {
                "request": request,
                "user": None,
                "questions": [],
                "categories": categories,
                "selected_category": None,
                "search_query": '',
                "selected_status": None,
                "current_page": 1,
                "total_pages": 1,
                "total_count": 0,
                "stats": {'total': 0, 'open': 0, 'closed': 0}
            }
        )

@router.post("/api/community/ask")
async def api_ask_question(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    primary_category_id: Optional[int] = Form(None),  # ✅ Categoria principale
    category_id: Optional[int] = Form(None)  # ✅ Sottocategoria
):
    """API per creare nuova domanda"""
    
    try:
        # Verifica autenticazione
        current_user = verify_token(request)
        
        if not current_user:
            return JSONResponse(
                {"error": "Devi essere loggato per fare una domanda"},
                status_code=401
            )
        
        # Validazione
        if len(title) < 10:
            return JSONResponse(
                {"error": "Il titolo deve essere di almeno 10 caratteri"},
                status_code=400
            )
        
        if len(description) < 20:
            return JSONResponse(
                {"error": "La descrizione deve essere di almeno 20 caratteri"},
                status_code=400
            )
        
        with get_session() as session:
            # Crea domanda
            new_question = CommunityQuestion(
                user_id=current_user.id,
                title=title,
                description=description,  # ✅ Usa description invece di content
                primary_category_id=primary_category_id,  # ✅ Salva categoria principale
                category_id=category_id,  # ✅ Salva subcategoria
                status=QuestionStatus.OPEN
            )
            
            session.add(new_question)
            session.commit()
            session.refresh(new_question)
            
            logger.info(
                f"✅ New question created: ID {new_question.id} "
                f"by user {current_user.email}"
            )
            
            return JSONResponse({
                "success": True,
                "message": "Domanda pubblicata con successo!",
                "question_id": new_question.id,
                "redirect_url": "/community"
            }, status_code=201)
    
    except Exception as e:
        logger.error(f"❌ Error creating question: {e}", exc_info=True)
        return JSONResponse(
            {"error": "Errore durante la pubblicazione della domanda"},
            status_code=500
        )

@router.post("/api/community/{question_id}/view")
async def increment_view(question_id: int):
    """Incrementa counter visualizzazioni"""
    
    try:
        with get_session() as session:
            question = session.get(CommunityQuestion, question_id)
            
            if not question:
                return JSONResponse({"error": "Domanda non trovata"}, status_code=404)
            
            question.increment_views()
            session.add(question)
            session.commit()
            
            return JSONResponse({"success": True, "views": question.views})
    
    except Exception as e:
        logger.error(f"Error incrementing view: {e}")
        return JSONResponse({"error": "Errore"}, status_code=500)


@router.post("/api/community/{question_id}/like")
async def toggle_like(request: Request, question_id: int):
    """
    Mette o toglie like a una domanda della community.
    Un utente può mettere un solo like per domanda.
    Se l'utente ha già messo like, lo rimuove (toggle).
    """
    
    try:
        # Verifica autenticazione
        current_user = verify_token(request)
        if not current_user:
            return JSONResponse({"error": "Non autenticato"}, status_code=401)
        
        with get_session() as session:
            # Verifica che la domanda esista
            question = session.get(CommunityQuestion, question_id)
            if not question:
                return JSONResponse({"error": "Domanda non trovata"}, status_code=404)
            
            # Verifica se l'utente ha già messo like
            existing_like = session.exec(
                select(CommunityLike).where(
                    and_(
                        CommunityLike.question_id == question_id,
                        CommunityLike.user_id == current_user.id
                    )
                )
            ).first()
            
            if existing_like:
                # ❌ Rimuovi like (toggle off)
                session.delete(existing_like)
                question.upvotes = max(0, question.upvotes - 1)
                action = "removed"
                logger.info(f"❌ User {current_user.id} removed like from question {question_id}")
            else:
                # ✅ Aggiungi like
                new_like = CommunityLike(
                    question_id=question_id,
                    user_id=current_user.id
                )
                session.add(new_like)
                question.upvotes += 1
                action = "added"
                logger.info(f"✅ User {current_user.id} liked question {question_id}")
            
            session.add(question)
            session.commit()
            
            return JSONResponse({
                "success": True,
                "action": action,
                "upvotes": question.upvotes,
                "user_liked": (action == "added")
            })
    
    except Exception as e:
        logger.error(f"Error toggling like: {e}")
        return JSONResponse({"error": "Errore durante l'operazione"}, status_code=500)


@router.post("/api/community/{question_id}/contact")
async def track_contact(request: Request, question_id: int):
    """
    Traccia quando un utente clicca sul tasto 'Messaggia'.
    Ogni utente può incrementare il contatore una sola volta per domanda.
    """
    try:
        # Verifica utente loggato
        current_user = verify_token(request)
        if not current_user:
            return JSONResponse({"error": "Non autenticato"}, status_code=401)
        
        with get_session() as session:
            # Trova la domanda
            question = session.get(CommunityQuestion, question_id)
            if not question:
                return JSONResponse({"error": "Domanda non trovata"}, status_code=404)
            
            # Verifica se l'utente ha già contattato (per incrementare counter solo prima volta)
            existing_contact = session.exec(
                select(CommunityContact).where(
                    and_(
                        CommunityContact.question_id == question_id,
                        CommunityContact.user_id == current_user.id
                    )
                )
            ).first()
            
            if not existing_contact:
                # Crea nuovo contatto e incrementa counter (SOLO PRIMA VOLTA)
                new_contact = CommunityContact(
                    question_id=question_id,
                    user_id=current_user.id
                )
                session.add(new_contact)
                question.views += 1
                session.add(question)
                session.commit()
                
                logger.info(f"✅ User {current_user.id} contacted author of question {question_id} (first time)")
                
                return JSONResponse({
                    "success": True,
                    "action": "tracked",
                    "contacts": question.views
                })
            else:
                # Già contattato, non incrementa counter
                logger.info(f"User {current_user.id} already contacted author of question {question_id}")
                
                return JSONResponse({
                    "success": True,
                    "action": "already_tracked",
                    "contacts": question.views
                })
    
    except Exception as e:
        logger.error(f"Error tracking contact: {e}")
        return JSONResponse({"error": "Errore durante l'operazione"}, status_code=500)

@router.get("/api/community/question-page")
async def get_question_page(
    question_id: int = Query(...),
    category: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """Trova il numero di pagina di una domanda specifica basato sui filtri attuali"""
    
    try:
        with get_session() as session:
            # ========== BASE QUERY ==========
            query_stmt = select(CommunityQuestion.id).order_by(
                CommunityQuestion.created_at.desc()
            )
            
            # ========== FILTRO CATEGORIA ==========
            if category:
                query_stmt = query_stmt.where(CommunityQuestion.category_id == category)
            
            # ========== FILTRO STATUS ==========
            if status and status in ['open', 'in_progress', 'closed']:
                query_stmt = query_stmt.where(CommunityQuestion.status == status)
            
            # ========== RICERCA ==========
            if search:
                search_pattern = f"%{search}%"
                query_stmt = query_stmt.where(
                    or_(
                        CommunityQuestion.title.ilike(search_pattern),
                        CommunityQuestion.description.ilike(search_pattern)
                    )
                )
            
            # ========== ESEGUI QUERY PER TROVARE LA POSIZIONE ==========
            all_question_ids = session.exec(query_stmt).all()
            
            # Trova l'indice della domanda
            try:
                index = all_question_ids.index(question_id)
            except ValueError:
                # La domanda non esiste con questi filtri
                return JSONResponse({
                    "success": False,
                    "error": "Domanda non trovata con i filtri attuali"
                }, status_code=404)
            
            # ========== CALCOLA LA PAGINA ==========
            per_page = 10
            page = (index // per_page) + 1
            
            return JSONResponse({
                "success": True,
                "page": page,
                "question_id": question_id
            })
    
    except Exception as e:
        logger.error(f"Error getting question page: {e}")
        return JSONResponse({"error": "Errore durante l'operazione"}, status_code=500)


@router.post("/api/community/{question_id}/follow")
async def toggle_follow_question(request: Request, question_id: int):
    """Toggle follow di una domanda - Segui e Richiedi"""
    try:
        user = verify_token(request)
        
        if not user:
            return JSONResponse({"error": "Non autenticato"}, status_code=401)
        
        with get_session() as session:
            from app.models import CommunityQuestion, CommunityQuestionFollow
            
            # Verifica che la domanda esista
            question = session.get(CommunityQuestion, question_id)
            if not question:
                return JSONResponse({"error": "Domanda non trovata"}, status_code=404)
            
            # Controlla se l'utente ha già seguito questa domanda
            existing_follow = session.exec(
                select(CommunityQuestionFollow).where(
                    (CommunityQuestionFollow.question_id == question_id) &
                    (CommunityQuestionFollow.user_id == user.id)
                )
            ).first()
            
            if existing_follow:
                # Rimuovi il follow
                session.delete(existing_follow)
                session.commit()
                followed = False
            else:
                # Aggiungi il follow
                follow = CommunityQuestionFollow(
                    question_id=question_id,
                    user_id=user.id
                )
                session.add(follow)
                session.commit()
                followed = True
            
            # Conta i follow totali
            follow_count = session.exec(
                select(func.count(CommunityQuestionFollow.id)).where(
                    CommunityQuestionFollow.question_id == question_id
                )
            ).first() or 0
            
            return JSONResponse({
                "success": True,
                "followed": followed,
                "follow_count": follow_count
            })
    
    except Exception as e:
        logger.error(f"Error toggling follow: {e}")
        return JSONResponse({"error": "Errore durante l'operazione"}, status_code=500)


@router.get("/api/community/{question_id}/follow-count")
async def get_follow_count(request: Request, question_id: int):
    """Recupera il numero di persone che hanno seguito una domanda"""
    try:
        with get_session() as session:
            from app.models import CommunityQuestion, CommunityQuestionFollow
            
            # Verifica che la domanda esista
            question = session.get(CommunityQuestion, question_id)
            if not question:
                return JSONResponse({"error": "Domanda non trovata"}, status_code=404)
            
            # Conta i follow
            follow_count = session.exec(
                select(func.count(CommunityQuestionFollow.id)).where(
                    CommunityQuestionFollow.question_id == question_id
                )
            ).first() or 0
            
            # Controlla se l'utente attuale ha seguito
            user_has_followed = False
            user = verify_token(request)
            if user:
                user_has_followed = session.exec(
                    select(CommunityQuestionFollow).where(
                        (CommunityQuestionFollow.question_id == question_id) &
                        (CommunityQuestionFollow.user_id == user.id)
                    )
                ).first() is not None
            
            return JSONResponse({
                "success": True,
                "follow_count": follow_count,
                "user_has_followed": user_has_followed
            })
    
    except Exception as e:
        logger.error(f"Error getting follow count: {e}")
        return JSONResponse({"error": "Errore durante l'operazione"}, status_code=500)


@router.get("/api/community/{question_id}/followers")
async def get_question_followers(request: Request, question_id: int):
    """Recupera la lista di utenti interessati a una domanda"""
    try:
        user = verify_token(request)
        
        if not user:
            return JSONResponse({"error": "Non autenticato"}, status_code=401)
        
        # Solo gli utenti verificati (consulenti) possono vedere questa lista
        if not user.is_verified:
            return JSONResponse({"error": "Solo i consulenti possono visualizzare questa lista"}, status_code=403)
        
        with get_session() as session:
            from app.models import CommunityQuestion, CommunityQuestionFollow, User as UserModel
            
            # Verifica che la domanda esista
            question = session.get(CommunityQuestion, question_id)
            if not question:
                return JSONResponse({"error": "Domanda non trovata"}, status_code=404)
            
            # Recupera tutti gli utenti che hanno seguito questa domanda
            followers = session.exec(
                select(UserModel)
                .join(CommunityQuestionFollow, CommunityQuestionFollow.user_id == UserModel.id)
                .where(CommunityQuestionFollow.question_id == question_id)
                .order_by(CommunityQuestionFollow.created_at.desc())
            ).all()
            
            followers_data = []
            for follower in followers:
                followers_data.append({
                    "id": follower.id,
                    "nome": follower.nome or "",
                    "cognome": follower.cognome or "",
                    "email": follower.email,
                    "profile_picture": follower.profile_picture or "/static/default-avatar.png",
                    "professione": follower.professione or "Utente"
                })
            
            return JSONResponse({
                "success": True,
                "followers": followers_data
            })
    
    except Exception as e:
        logger.error(f"Error getting followers: {e}")
        return JSONResponse({"error": "Errore durante l'operazione"}, status_code=500)

