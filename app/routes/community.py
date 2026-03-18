from fastapi import APIRouter, Request, Form, Query, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel import select, func, or_, and_
from sqlalchemy import cast, String
from typing import Optional, List
from datetime import datetime, timedelta
import os
import json
import base64

from app.database import get_session
from app.models import User, Category, CommunityQuestion, CommunityLike, CommunityContact, CommunityQuestionFollow, QuestionStatus, CategoryHierarchy, CategoryRequestNotification
from app.routes.auth import verify_token
from app.utils_user import get_display_name
from app.utils.email import send_email
from app.utils.ai_service import genera_tags, modera_immagine, valida_richiesta, controlla_duplicato
from loguru import logger

router = APIRouter()

@router.get("/community", response_class=HTMLResponse)
async def community_page(
    request: Request,
    category: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort: Optional[str] = Query(None),
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
            base_where = CommunityQuestion.validation == True  # 🆕 Mostra solo domande validate
            
            # ========== ORDINAMENTO ==========
            if sort == 'interactions':
                # Ordina per interazioni (upvotes + views/contatti)
                query_stmt = select(CommunityQuestion).where(base_where).order_by(
                    (CommunityQuestion.upvotes + CommunityQuestion.views).desc(),
                    CommunityQuestion.created_at.desc()
                )
            elif sort == 'followed':
                # Ordina per numero di follower (subquery)
                follow_count_subq = (
                    select(
                        CommunityQuestionFollow.question_id,
                        func.count(CommunityQuestionFollow.id).label('follow_count')
                    )
                    .group_by(CommunityQuestionFollow.question_id)
                    .subquery()
                )
                query_stmt = (
                    select(CommunityQuestion)
                    .outerjoin(follow_count_subq, CommunityQuestion.id == follow_count_subq.c.question_id)
                    .where(base_where)
                    .order_by(
                        func.coalesce(follow_count_subq.c.follow_count, 0).desc(),
                        CommunityQuestion.created_at.desc()
                    )
                )
            else:
                # Default: più recenti
                query_stmt = select(CommunityQuestion).where(base_where).order_by(
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
                            cast(User.selected_subcategories, String).like(f'%{category}%')  # Tra le subcategorie
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
                # Calcola inizio della giornata corrente (mezzanotte)
                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                
                logger.info(f"🔍 Checking questions for user {current_user.id} since {today_start}")
                
                # Recupera le domande dell'utente nella giornata corrente
                user_recent_questions = session.exec(
                    select(CommunityQuestion)
                    .where(
                        and_(
                            CommunityQuestion.user_id == current_user.id,
                            CommunityQuestion.created_at >= today_start
                        )
                    )
                ).all()
                
                user_questions_count = len(user_recent_questions)
                
                # Log dettaglio domande
                for q in user_recent_questions:
                    logger.info(f"  📝 Question ID {q.id}: '{q.title}' - Created: {q.created_at}")
                
                # Se ha già fatto 5 o più domande oggi, non può crearne altre
                can_create_question = user_questions_count < 5
                
                logger.info(
                    f"👤 User {current_user.nome} (ID: {current_user.id}) - Questions today: {user_questions_count}/5 "
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
                    "selected_sort": sort or 'recent',
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
        logger.error(f"❌ Error loading community page: {str(e)}", exc_info=True)
        
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
    category_id: Optional[int] = Form(None),  # ✅ Sottocategoria
    images: Optional[str] = Form(None)  # JSON array di URL S3 delle immagini
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
        
        # ========== CONTROLLO LIMITE GIORNALIERO ==========
        with get_session() as session:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            user_today_questions = session.exec(
                select(CommunityQuestion)
                .where(
                    and_(
                        CommunityQuestion.user_id == current_user.id,
                        CommunityQuestion.created_at >= today_start
                    )
                )
            ).all()
            
            if len(user_today_questions) >= 5:
                return JSONResponse(
                    {"error": "Hai raggiunto il limite di 5 richieste al giorno. Riprova domani!"},
                    status_code=429
                )
            
            # ========== CONTROLLO DUPLICATO AI ==========
            # Recupera tutte le domande precedenti dell'utente
            all_user_questions = session.exec(
                select(CommunityQuestion)
                .where(CommunityQuestion.user_id == current_user.id)
                .order_by(CommunityQuestion.created_at.desc())
                .limit(50)
            ).all()
            
            domande_precedenti = [
                {"title": q.title, "description": q.description}
                for q in all_user_questions
            ]
        
        if domande_precedenti:
            duplicato = await controlla_duplicato(title, description, domande_precedenti)
            if duplicato.get("is_duplicate", False):
                reason = duplicato.get("reason", "Richiesta simile già presente")
                logger.warning(f"🔴 Richiesta duplicata per user {current_user.id}: {reason}")
                return JSONResponse(
                    {"error": f"{reason}. Prova a formulare una richiesta diversa."},
                    status_code=400
                )
        
        # ========== VALIDAZIONE AI DEL CONTENUTO ==========
        validazione = await valida_richiesta(title, description)
        is_validated = validazione.get("approved", True)
        
        if not is_validated:
            reason = validazione.get("reason", "Contenuto non approvato")
            logger.warning(f"🚫 Richiesta rifiutata per user {current_user.id}: {reason}")
            return JSONResponse(
                {"error": f"La tua richiesta non è stata approvata: {reason}"},
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
                images=images if images else None,  # ✅ Salva URL immagini S3
                status=QuestionStatus.OPEN,
                validation=True  # ✅ Approvata dall'AI, visibile subito
            )
            
            session.add(new_question)
            session.commit()
            session.refresh(new_question)
            
            logger.info(
                f"✅ New question created: ID {new_question.id} "
                f"by user {current_user.email}"
            )
            
            # ========== NOTIFICA CONSULENTI ==========
            # Trova tutti i consulenti che hanno la stessa categoria e notify_category_requests=true
            category_to_search = primary_category_id or category_id
            
            if category_to_search:
                consultants = session.exec(
                    select(User).where(
                        and_(
                            or_(
                                User.category_id == category_to_search,
                                # Se la categoria è una sottocategoria, cerca anche per categoria principale
                            ),
                            User.is_verified == True,
                            User.notify_category_requests == True,
                            User.id != current_user.id  # Non notificare l'autore della domanda
                        )
                    )
                ).all()
                
                logger.info(f"🔔 Found {len(consultants)} consultants to notify for category {category_to_search}")
                
                # Crea notifiche e invia mail
                for consultant in consultants:
                    # Crea record di notifica
                    notification = CategoryRequestNotification(
                        consultant_user_id=consultant.id,
                        question_id=new_question.id,
                        is_read=False
                    )
                    session.add(notification)
                    
                    # Invia email
                    try:
                        send_email(
                            recipient_email=consultant.email,
                            subject=f"🔔 Nuova richiesta di consulenza nella tua categoria: {new_question.title}",
                            html_content=f"""
                            <html>
                                <body style="font-family: Arial, sans-serif;">
                                    <div style="max-width: 600px; margin: 0 auto;">
                                        <h2>Nuova Richiesta di Consulenza</h2>
                                        <p>Ciao {consultant.nome},</p>
                                        <p>C'è una nuova richiesta di consulenza nella tua categoria di expertise!</p>
                                        
                                        <div style="background: #f0f0f0; padding: 16px; border-radius: 8px; margin: 20px 0;">
                                            <h3 style="margin-top: 0;">{new_question.title}</h3>
                                            <p>{new_question.description[:200]}...</p>
                                            <p><strong>Utente:</strong> {current_user.nome} {current_user.cognome}</p>
                                        </div>
                                        
                                        <p>
                                            <a href="{os.getenv('APP_URL', 'http://localhost:8000')}/profile" 
                                               style="background: #4caf50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                                                Visualizza Richieste
                                            </a>
                                        </p>
                                        
                                        <p>Accedi al tuo profilo per vedere tutte le nuove richieste della tua categoria.</p>
                                    </div>
                                </body>
                            </html>
                            """
                        )
                        logger.info(f"📧 Email sent to consultant {consultant.email}")
                    except Exception as e:
                        logger.error(f"❌ Error sending email to {consultant.email}: {e}")
                
                session.commit()
            
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

@router.post("/api/community/upload-image")
async def upload_community_image(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(""),
    description: str = Form("")
):
    """
    Upload di un'immagine per una richiesta della community.
    L'immagine viene moderata tramite AI prima di essere salvata su S3.
    """
    try:
        # Verifica autenticazione
        current_user = verify_token(request)
        if not current_user:
            return JSONResponse({"error": "Devi essere loggato"}, status_code=401)
        
        # Verifica formato file
        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        if file.content_type not in allowed_types:
            return JSONResponse(
                {"error": "Formato non supportato. Usa JPG, PNG o WebP."},
                status_code=400
            )
        
        # Leggi il file
        contents = await file.read()
        
        # Max 5MB
        if len(contents) > 5 * 1024 * 1024:
            return JSONResponse(
                {"error": "File troppo grande. Massimo 5MB."},
                status_code=400
            )
        
        # ========== MODERAZIONE AI ==========
        image_b64 = base64.b64encode(contents).decode("utf-8")
        moderation = await modera_immagine(image_b64, title, description)
        
        if not moderation.get("approved", False):
            reason = moderation.get("reason", "Immagine non approvata")
            logger.warning(f"🚫 Immagine rifiutata per user {current_user.id}: {reason}")
            return JSONResponse(
                {"error": f"Immagine rifiutata: {reason}"},
                status_code=400
            )
        
        # ========== UPLOAD SU S3 ==========
        import boto3
        
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        s3_bucket = os.getenv("S3_BUCKET_NAME", "helpy-images")
        s3_region = os.getenv("AWS_REGION", "eu-west-1")
        
        if not aws_access_key or not aws_secret_key:
            logger.error("❌ AWS credentials non configurate per upload community")
            return JSONResponse(
                {"error": "Servizio di upload non disponibile"},
                status_code=500
            )
        
        try:
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=s3_region
            )
            
            # Genera nome unico
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            file_extension = file.filename.split(".")[-1].lower() if file.filename else "jpg"
            s3_key = f"community-images/{current_user.id}_{timestamp}.{file_extension}"
            
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=s3_key,
                Body=contents,
                ContentType=file.content_type,
                CacheControl="max-age=31536000"
            )
            
            s3_url = f"https://{s3_bucket}.s3.{s3_region}.amazonaws.com/{s3_key}"
            logger.info(f"✅ Immagine community caricata su S3: {s3_url}")
            
            return JSONResponse({
                "success": True,
                "url": s3_url
            })
            
        except Exception as e:
            logger.error(f"❌ Errore upload S3: {e}")
            return JSONResponse(
                {"error": "Errore durante il caricamento dell'immagine"},
                status_code=500
            )
    
    except Exception as e:
        logger.error(f"❌ Errore upload immagine community: {e}", exc_info=True)
        return JSONResponse(
            {"error": "Errore durante il caricamento"},
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


@router.post("/api/community/generate-tags")
async def generate_question_tags(request: Request):
    """Genera tag per una domanda della community usando AI"""
    try:
        user = verify_token(request)
        if not user:
            return JSONResponse({"error": "Non autenticato"}, status_code=401)
        
        body = await request.json()
        titolo = body.get("titolo", "").strip()
        descrizione = body.get("descrizione", "").strip()
        categoria = body.get("categoria", "").strip()
        
        if not titolo or not descrizione:
            return JSONResponse(
                {"error": "Inserisci titolo e descrizione per generare i tag."},
                status_code=400
            )
        
        # Combina titolo e descrizione come "descrizione" per il servizio AI
        testo_completo = f"{titolo}. {descrizione}"
        
        tags = await genera_tags(
            descrizione=testo_completo,
            aree_interesse=categoria,
            professione=None
        )
        
        # Limita a 8 tag per le domande community
        tags = tags[:8]
        
        return JSONResponse({
            "success": True,
            "tags": tags,
            "tags_string": ", ".join(tags)
        })
    
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    except Exception as e:
        logger.error(f"❌ Errore generazione tags community: {e}", exc_info=True)
        return JSONResponse(
            {"error": "Errore durante la generazione dei tag. Riprova."},
            status_code=500
        )


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
                # Determina avatar di default in base al genere
                if hasattr(follower, 'genere') and follower.genere == 'M':
                    default_pic = "/static/avatar-male.svg"
                elif hasattr(follower, 'genere') and follower.genere == 'F':
                    default_pic = "/static/avatar-female.svg"
                else:
                    default_pic = "/static/avatar-default.svg"
                
                followers_data.append({
                    "id": follower.id,
                    "nome": follower.nome or "",
                    "cognome": follower.cognome or "",
                    "email": follower.email,
                    "profile_picture": follower.profile_picture or default_pic,
                    "professione": follower.professione or "Utente"
                })
            
            return JSONResponse({
                "success": True,
                "followers": followers_data
            })
    
    except Exception as e:
        logger.error(f"Error getting followers: {e}")
        return JSONResponse({"error": "Errore durante l'operazione"}, status_code=500)

