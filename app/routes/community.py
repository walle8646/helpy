from fastapi import APIRouter, Request, Form, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel import select, func, or_, and_
from typing import Optional
from datetime import datetime, timedelta
import os

from app.database import get_session
from app.models import User, Category, CommunityQuestion, CommunityLike, CommunityContact, QuestionStatus
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
            # ========== CARICA CATEGORIE ==========
            categories = session.exec(
                select(Category).order_by(Category.name)
            ).all()
            
            # ========== BASE QUERY ==========
            query_stmt = select(CommunityQuestion).order_by(
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
            
            # ========== COUNT TOTALE ==========
            count_query = select(func.count(CommunityQuestion.id))
            
            if category:
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
            
            # ========== TOP CONSULTANTS ==========
            top_consultants = session.exec(
                select(User)
                .where(User.bollini > 0)
                .order_by(User.bollini.desc())
                .limit(3)
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
    category_id: Optional[int] = Form(None)
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
                category_id=category_id,
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
