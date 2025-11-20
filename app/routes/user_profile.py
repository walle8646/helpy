from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.database import get_session
from app.models import User, Category
from sqlmodel import select
from app.routes.auth import verify_token
from app.logger_config import logger
from app.utils.email import send_profile_verification_request
from typing import Optional
import os
import hashlib
from PIL import Image
import io

router = APIRouter()

@router.get("/profile", response_class=HTMLResponse)
async def user_profile(request: Request):
    """Pagina profilo utente"""
    try:
        user = verify_token(request)
        
        if not user:
            logger.warning("❌ Unauthorized access to profile")
            return RedirectResponse("/login", status_code=307)
        
        with get_session() as session:
            fresh_user = session.get(User, user.id)
            
            if not fresh_user:
                logger.error(f"❌ User ID {user.id} not found in database")
                request.session.clear()
                return RedirectResponse("/login", status_code=307)
            
            categories = session.exec(select(Category)).all()
            logger.info(f"✅ Loaded {len(categories)} categories")
            
            # ✅ AGGIUNGI cognome
            user_data = {
                "id": fresh_user.id,
                "email": fresh_user.email,
                "nome": fresh_user.nome or "",
                "cognome": fresh_user.cognome or "",  # ✅ AGGIUNGI questo
                "professione": fresh_user.professione or "",
                "descrizione": fresh_user.descrizione or "",
                "profile_picture": fresh_user.profile_picture or "/static/default-avatar.png",
                "category_id": fresh_user.category_id,
                "aree_interesse": fresh_user.aree_interesse or "",
                "prezzo_consulenza": fresh_user.prezzo_consulenza or 0,
                "bollini": fresh_user.bollini or 0,
                "confirmed": fresh_user.confirmed,
                "created_at": fresh_user.created_at.strftime("%d/%m/%Y") if fresh_user.created_at else "N/A"
            }
            
            logger.info(f"✅ Profile loaded for user: {fresh_user.email}")
            
            return request.app.state.templates.TemplateResponse(
                "profile.html",
                {
                    "request": request,
                    "user": user_data,  # Dati del proprio profilo
                    "current_user": fresh_user,  # Per il navbar
                    "categories": categories
                }
            )
    
    except Exception as e:
        logger.error(f"Error in profile: {e}", exc_info=True)
        request.session.clear()
        return RedirectResponse("/login", status_code=307)

@router.get("/api/profile/liked-questions")
async def get_liked_questions(request: Request):
    """Recupera le ultime 6 domande a cui l'utente ha messo like"""
    try:
        user = verify_token(request)
        
        if not user:
            return JSONResponse({"error": "Non autenticato"}, status_code=401)
        
        with get_session() as session:
            from app.models import CommunityQuestion, CommunityLike, User as UserModel
            
            # Query per recuperare le ultime 6 domande amate ordinate per data decrescente
            liked_questions = session.exec(
                select(CommunityQuestion)
                .join(CommunityLike, CommunityQuestion.id == CommunityLike.question_id)
                .where(CommunityLike.user_id == user.id)
                .order_by(CommunityLike.created_at.desc())
                .limit(6)
            ).all()
            
            questions_data = []
            for q in liked_questions:
                # Recupera l'autore della domanda
                author = session.get(UserModel, q.user_id)
                
                questions_data.append({
                    "id": q.id,
                    "title": q.title,
                    "description": q.description[:150] + "..." if len(q.description) > 150 else q.description,  # Preview
                    "author_name": author.nome if author else "Utente Anonimo",
                    "author_id": q.user_id,
                    "category_id": q.category_id,
                    "upvotes": q.upvotes,
                    "views": q.views,
                    "created_at": q.created_at.strftime("%d/%m/%Y"),
                    "url": f"/community/question/{q.id}"
                })
            
            return JSONResponse({
                "success": True,
                "questions": questions_data
            })
    
    except Exception as e:
        logger.error(f"Error getting liked questions: {e}", exc_info=True)
        return JSONResponse(
            {"error": "Errore nel recupero delle domande"},
            status_code=500
        )

@router.post("/api/profile/update")
async def update_profile(
    request: Request,
    nome: str = Form(None),
    cognome: str = Form(None),  # ✅ AGGIUNGI cognome
    professione: str = Form(None),
    descrizione: str = Form(None),
    category_id: Optional[int] = Form(None),
    aree_interesse: str = Form(None),
    prezzo_consulenza: Optional[int] = Form(None),
    is_anonymous: Optional[bool] = Form(None)  # ✅ NUOVO: flag anonimato
):
    """Aggiorna profilo utente"""
    try:
        user = verify_token(request)
        
        if not user:
            return JSONResponse({"error": "Non autenticato"}, status_code=401)
        
        with get_session() as session:
            db_user = session.get(User, user.id)
            
            if not db_user:
                return JSONResponse({"error": "Utente non trovato"}, status_code=404)
            
            # Check if user was already verified before update
            was_verified_before = db_user.is_verified
            
            if nome is not None:
                db_user.nome = nome
            if cognome is not None:  # ✅ AGGIUNGI questo
                db_user.cognome = cognome
            if professione is not None:
                db_user.professione = professione
            if descrizione is not None:
                db_user.descrizione = descrizione
            if category_id is not None:
                db_user.category_id = category_id
            if aree_interesse is not None:
                db_user.aree_interesse = aree_interesse
            if prezzo_consulenza is not None:
                db_user.prezzo_consulenza = prezzo_consulenza
            if is_anonymous is not None:  # ✅ NUOVO: aggiorna flag anonimato
                db_user.is_anonymous = is_anonymous
                logger.info(f"{'🔒' if is_anonymous else '👤'} User {db_user.id} set anonymous mode: {is_anonymous}")
            
            session.add(db_user)
            session.commit()
            session.refresh(db_user)
            
            logger.info(f"✅ Profile updated for user: {db_user.email}")
            
            # 🔍 DEBUG: Log dello stato di verifica
            logger.info(f"🔍 DEBUG - was_verified_before: {was_verified_before}")
            logger.info(f"🔍 DEBUG - is_verified (current): {db_user.is_verified}")
            logger.info(f"🔍 DEBUG - user_type_id: {db_user.user_type_id}")
            
            # Check if profile meets verification criteria
            has_professione = db_user.professione and db_user.professione.strip() != ""
            has_category = db_user.category_id is not None
            has_aree_interesse = db_user.aree_interesse and db_user.aree_interesse.strip() != ""
            has_descrizione = db_user.descrizione and len(db_user.descrizione.strip()) >= 200
            
            logger.info(f"🔍 DEBUG - Professione filled: {has_professione} (value: '{db_user.professione}')")
            logger.info(f"🔍 DEBUG - Category selected: {has_category} (value: {db_user.category_id})")
            logger.info(f"🔍 DEBUG - Aree interesse filled: {has_aree_interesse} (value: '{db_user.aree_interesse}')")
            logger.info(f"🔍 DEBUG - Descrizione ≥200: {has_descrizione} (length: {len(db_user.descrizione.strip()) if db_user.descrizione else 0})")
            
            profile_complete = has_professione and has_category and has_aree_interesse and has_descrizione
            logger.info(f"🔍 DEBUG - profile_complete: {profile_complete}")
            logger.info(f"🔍 DEBUG - should send email: {profile_complete and not was_verified_before}")
            
            # Send notification to verifiers if criteria met and not already verified
            if profile_complete and not was_verified_before:
                logger.info(f"🔍 Profile verification criteria met for user {db_user.email}")
                
                # Get all verifiers and admins (user_type_id 2 and 3)
                verifiers = session.exec(
                    select(User).where(User.user_type_id.in_([2, 3]))
                ).all()
                
                logger.info(f"🔍 DEBUG - Found {len(verifiers)} verifiers in database")
                for v in verifiers:
                    logger.info(f"  - Verifier: {v.email} (user_type_id: {v.user_type_id})")
                
                if verifiers:
                    user_full_name = f"{db_user.nome or ''} {db_user.cognome or ''}".strip() or "Utente"
                    
                    for verifier in verifiers:
                        if verifier.email:
                            try:
                                logger.info(f"📧 Attempting to send email to {verifier.email}...")
                                send_profile_verification_request(
                                    to_email=verifier.email,
                                    user_id=db_user.id,
                                    user_name=user_full_name,
                                    user_email=db_user.email
                                )
                                logger.info(f"✅ Verification request sent to {verifier.email}")
                            except Exception as e:
                                logger.error(f"❌ Failed to send email to {verifier.email}: {e}", exc_info=True)
                        else:
                            logger.warning(f"⚠️ Verifier ID {verifier.id} has no email address")
                else:
                    logger.warning("⚠️ No verifiers found in the system (user_type_id 2 or 3)")
            elif not profile_complete:
                logger.info("ℹ️ Profile not complete, email not sent")
            elif was_verified_before:
                logger.info("ℹ️ User already verified, email not sent")
            
            return JSONResponse({
                "message": "Profilo aggiornato con successo!",
                "user": {
                    "nome": db_user.nome,
                    "cognome": db_user.cognome,  # ✅ AGGIUNGI questo
                    "professione": db_user.professione
                },
                "verification_requested": profile_complete and not was_verified_before
            })
    
    except Exception as e:
        logger.error(f"Error updating profile: {e}", exc_info=True)
        return JSONResponse(
            {"error": "Errore durante l'aggiornamento"},
            status_code=500
        )