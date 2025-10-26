from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.database import get_session
from app.models import User
from sqlmodel import select
import hashlib
from typing import Optional
from app.logger_config import logger
from app.utils.email import generate_verification_code, send_verification_email

router = APIRouter()

def verify_token(request: Request) -> Optional[User]:
    """Verifica se l'utente è loggato tramite session"""
    user_id = request.session.get("user_id")
    
    if not user_id:
        return None
    
    with get_session() as session:
        user = session.get(User, user_id)
        return user

async def get_current_user(request: Request) -> User:
    """Dependency che richiede autenticazione"""
    user = verify_token(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    return user

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Pagina di login"""
    return request.app.state.templates.TemplateResponse(
        "login.html",
        {"request": request}
    )

@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    """Login con form HTML"""
    with get_session() as session:
        statement = select(User).where(User.email == email)
        user = session.exec(statement).first()
        
        if not user:
            return request.app.state.templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Email non trovata"}
            )
        
        password_hash = hashlib.md5(password.encode()).hexdigest()
        
        if user.password_md5 != password_hash:
            return request.app.state.templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Password errata"}
            )
        
        if user.confirmed != 1:
            return request.app.state.templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Conferma prima la tua email"}
            )
        
        request.session["user_id"] = user.id
        request.session["user_email"] = user.email
        request.session["user_nome"] = user.nome or "User"
        
        logger.info(f"✅ User logged in: {user.email}")
        
        return RedirectResponse(url="/profile", status_code=303)

@router.post("/api/login")
async def api_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    """API Login (ritorna JSON)"""
    with get_session() as session:
        statement = select(User).where(User.email == email)
        user = session.exec(statement).first()
        
        if not user:
            return JSONResponse({"error": "Email non trovata"}, status_code=404)
        
        password_hash = hashlib.md5(password.encode()).hexdigest()
        
        if user.password_md5 != password_hash:
            return JSONResponse({"error": "Password errata"}, status_code=401)
        
        if user.confirmed != 1:
            return JSONResponse({"error": "Conferma la tua email"}, status_code=403)
        
        request.session["user_id"] = user.id
        request.session["user_email"] = user.email
        
        return JSONResponse({
            "message": "Login successful",
            "redirect_url": "/profile",
            "user": {
                "id": user.id,
                "email": user.email,
                "nome": user.nome
            }
        })

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Pagina di registrazione"""
    current_user = verify_token(request)
    
    if current_user:
        return RedirectResponse("/profile", status_code=302)
    
    return request.app.state.templates.TemplateResponse(
        "register.html",
        {"request": request}
    )

@router.post("/api/register")
async def api_register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    nome: str = Form(...),
    cognome: str = Form(None)  # ✅ AGGIUNGI cognome (opzionale)
):
    """API Registrazione con invio email di conferma"""
    try:
        with get_session() as session:
            existing = session.exec(select(User).where(User.email == email)).first()
            
            if existing:
                if existing.confirmed == 1:
                    logger.warning(f"❌ Registration attempt with existing email: {email}")
                    return JSONResponse({
                        "error": "Email già registrata",
                        "message": "Questa email è già registrata. Hai già un account?",
                        "redirect_url": "/login",
                        "show_login_link": True
                    }, status_code=400)
                else:
                    code = generate_verification_code()
                    existing.confirmation_code = code
                    session.add(existing)
                    session.commit()
                    
                    send_verification_email(email, code, existing.nome or "User")
                    
                    logger.info(f"♻️ Resent confirmation code to: {email}")
                    
                    return JSONResponse({
                        "message": "Codice di verifica inviato nuovamente!",
                        "email": email,
                        "requires_verification": True
                    }, status_code=200)
            
            password_hash = hashlib.md5(password.encode()).hexdigest()
            code = generate_verification_code()
            
            # ✅ AGGIUNGI cognome al nuovo utente
            new_user = User(
                email=email,
                password_md5=password_hash,
                nome=nome,
                cognome=cognome,  # ✅ AGGIUNGI questo
                confirmed=0,
                bollini=0,
                confirmation_code=code
            )
            
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            
            email_sent = send_verification_email(email, code, nome)
            
            if not email_sent:
                logger.warning(f"⚠️ User registered but email failed: {email}")
            
            logger.info(f"✅ New user registered: {email} (ID: {new_user.id}) - Code: {code}")
            
            return JSONResponse({
                "message": "Registrazione completata! Controlla la tua email per il codice di verifica.",
                "email": email,
                "requires_verification": True
            }, status_code=201)
    
    except Exception as e:
        logger.error(f"Error during registration: {e}", exc_info=True)
        return JSONResponse(
            {"error": "Errore durante la registrazione. Riprova."},
            status_code=500
        )

@router.post("/api/verify-email")
async def verify_email(
    request: Request,
    email: str = Form(...),
    code: str = Form(...)
):
    """Verifica codice email"""
    try:
        with get_session() as session:
            user = session.exec(select(User).where(User.email == email)).first()
            
            if not user:
                return JSONResponse({"error": "Email non trovata"}, status_code=404)
            
            if user.confirmed == 1:
                return JSONResponse({"error": "Email già verificata"}, status_code=400)
            
            if user.confirmation_code != code:
                logger.warning(f"❌ Invalid code for {email}")
                return JSONResponse({"error": "Codice non valido"}, status_code=400)
            
            user.confirmed = 1
            user.confirmation_code = None
            session.add(user)
            session.commit()
            
            request.session["user_id"] = user.id
            request.session["user_email"] = user.email
            request.session["user_nome"] = user.nome or "User"
            
            logger.info(f"✅ Email verified for: {email}")
            
            return JSONResponse({
                "message": "Email verificata con successo!",
                "redirect_url": "/profile"
            }, status_code=200)
    
    except Exception as e:
        logger.error(f"Error during verification: {e}", exc_info=True)
        return JSONResponse({"error": "Errore durante la verifica"}, status_code=500)

@router.post("/api/resend-verification")
async def resend_verification(
    request: Request,
    email: str = Form(...)
):
    """Reinvia codice di verifica"""
    try:
        with get_session() as session:
            user = session.exec(select(User).where(User.email == email)).first()
            
            if not user:
                return JSONResponse({"error": "Email non trovata"}, status_code=404)
            
            if user.confirmed == 1:
                return JSONResponse({"error": "Email già verificata"}, status_code=400)
            
            code = generate_verification_code()
            user.confirmation_code = code
            session.add(user)
            session.commit()
            
            send_verification_email(email, code, user.nome or "User")
            
            logger.info(f"♻️ Resent code to {email}")
            
            return JSONResponse({"message": "Codice inviato nuovamente!"}, status_code=200)
    
    except Exception as e:
        logger.error(f"Error resending code: {e}", exc_info=True)
        return JSONResponse({"error": "Errore. Riprova."}, status_code=500)

@router.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    nome: str = Form(...),
    cognome: str = Form(None)  # ✅ AGGIUNGI cognome
):
    """Registrazione con form HTML (redirect)"""
    with get_session() as session:
        existing = session.exec(select(User).where(User.email == email)).first()
        
        if existing:
            return request.app.state.templates.TemplateResponse(
                "register.html",
                {"request": request, "error": "Email già registrata"}
            )
        
        password_hash = hashlib.md5(password.encode()).hexdigest()
        
        # ✅ AGGIUNGI cognome
        new_user = User(
            email=email,
            password_md5=password_hash,
            nome=nome,
            cognome=cognome,  # ✅ AGGIUNGI questo
            confirmed=0,
            bollini=0
        )
        
        session.add(new_user)
        session.commit()
        
        logger.info(f"✅ New user registered (HTML): {email}")
        
        return RedirectResponse("/login?registered=true", status_code=302)

@router.get("/logout")
async def logout(request: Request):
    """Logout utente"""
    request.session.clear()
    return RedirectResponse("/", status_code=302)