from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.database import get_session
from app.models import User
from sqlmodel import select
import time
import hashlib
from typing import Optional
from app.logger_config import logger
from app.utils.email import generate_verification_code  # âœ… RIMUOVI send_verification_email da qui
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from loguru import logger
import jwt
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

router = APIRouter()

# Cache last_seen per evitare UPDATE al DB ad ogni richiesta
# Aggiorna last_seen solo ogni 5 minuti per utente
_last_seen_cache: dict[int, float] = {}
_LAST_SEEN_INTERVAL = 300  # 5 minuti in secondi

def verify_token(request: Request) -> Optional[User]:
    """
    Verifica token JWT e restituisce utente autenticato
    """
    try:
        # âœ… Leggi token dalla sessione
        token = request.session.get("access_token")
        
        if not token:
            logger.debug(f"Session keys: {list(request.session.keys())}")
            
            # Fallback: controlla se c'Ã¨ user_id nella sessione (sessione senza JWT)
            user_id = request.session.get("user_id")
            if user_id:
                with get_session() as session:
                    user = session.get(User, user_id)
                    if user:
                        _maybe_update_last_seen(session, user)
                        return user
            
            return None
        
        # Decodifica JWT
        JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            user_id = payload.get("user_id")
            
            if not user_id:
                logger.warning("âš ï¸ No user_id in token payload")
                return None
        
        except jwt.ExpiredSignatureError:
            logger.warning("âš ï¸ Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"âš ï¸ Invalid token: {str(e)}")
            return None
        
        # âœ… Ottieni utente dal database
        with get_session() as session:
            user = session.get(User, user_id)
            
            if not user:
                logger.warning(f"âš ï¸ User {user_id} not found in database")
                return None
            
            _maybe_update_last_seen(session, user)
            
            return user
    
    except Exception as e:
        logger.error("Error verifying token: " + str(e).replace("{", "{{").replace("}", "}}"), exc_info=True)
        return None


def _maybe_update_last_seen(session, user: User):
    """Aggiorna last_seen solo se sono passati piÃ¹ di 5 minuti dall'ultimo aggiornamento"""
    now = time.time()
    last_update = _last_seen_cache.get(user.id, 0)
    if now - last_update > _LAST_SEEN_INTERVAL:
        user.last_seen = datetime.utcnow()
        session.add(user)
        session.commit()
        session.refresh(user)
        _last_seen_cache[user.id] = now

# Alias per compatibilitÃ 
def get_current_user(request: Request) -> Optional[User]:
    """Alias di verify_token"""
    return verify_token(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    return user

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
        
        logger.info(f"âœ… User logged in: {user.email}")
        
        return RedirectResponse(url="/profile", status_code=303)

@router.post("/api/login")
async def api_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    """API endpoint per login (AJAX)"""
    try:
        with get_session() as session:
            user = session.exec(
                select(User).where(User.email == email)
            ).first()
            
            if not user:
                return JSONResponse(
                    {"error": "Email o password non corretti"},
                    status_code=401
                )
            
            # Verifica password
            password_hash = hashlib.md5(password.encode()).hexdigest()
            if user.password_md5 != password_hash:
                return JSONResponse(
                    {"error": "Email o password non corretti"},
                    status_code=401
                )
            
            # âœ… Genera token JWT
            JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
            token_data = {
                "user_id": user.id,
                "email": user.email,
                "exp": datetime.utcnow() + timedelta(days=7)
            }
            access_token = jwt.encode(token_data, JWT_SECRET, algorithm="HS256")
            
            # âœ… SALVA TOKEN IN SESSION (IMPORTANTE!)
            request.session["access_token"] = access_token
            request.session["user_id"] = user.id
            request.session["user_email"] = user.email
            request.session["user_nome"] = user.nome
            
            logger.info(f"âœ… User logged in: {user.nome} ({user.email})")
            logger.info(f"ðŸ”‘ Session data: {request.session}")  # Debug
            
            return JSONResponse({
                "success": True,
                "message": "Login effettuato con successo",
                "user": {
                    "id": user.id,
                    "nome": user.nome,
                    "email": user.email
                }
            }, status_code=200)
    
    except Exception as e:
        logger.error("Login error: " + str(e).replace("{", "{{").replace("}", "}}"), exc_info=True)
        return JSONResponse(
            {"error": "Errore durante il login"},
            status_code=500
        )

@router.post("/api/register")
async def api_register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    nome: str = Form(...),
    cognome: str = Form(None)
):
    """API Registrazione con invio email di conferma"""
    try:
        with get_session() as session:
            existing = session.exec(select(User).where(User.email == email)).first()
            
            if existing:
                if existing.confirmed == 1:
                    logger.warning(f"âŒ Registration attempt with existing email: {email}")
                    return JSONResponse({
                        "error": "Email giÃ  registrata",
                        "message": "Questa email Ã¨ giÃ  registrata. Hai giÃ  un account?",
                        "redirect_url": "/login",
                        "show_login_link": True
                    }, status_code=400)
                else:
                    code = generate_verification_code()
                    existing.confirmation_code = code
                    session.add(existing)
                    session.commit()
                    
                    # âœ… Ora funziona con 3 parametri
                    send_verification_email(email, code, existing.nome or "User")
                    
                    logger.info(f"â™»ï¸ Resent confirmation code to: {email}")
                    
                    return JSONResponse({
                        "message": "Codice di verifica inviato nuovamente!",
                        "email": email,
                        "requires_verification": True
                    }, status_code=200)
            
            password_hash = hashlib.md5(password.encode()).hexdigest()
            code = generate_verification_code()
            
            new_user = User(
                email=email,
                password_md5=password_hash,
                nome=nome,
                cognome=cognome,
                confirmed=0,
                confirmation_code=code
            )
            
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            
            # âœ… Ora funziona con 3 parametri
            email_sent = send_verification_email(email, code, nome)
            
            if not email_sent:
                logger.warning(f"âš ï¸ User registered but email failed: {email}")
            
            logger.info(f"âœ… New user registered: {email} (ID: {new_user.id}) - Code: {code}")
            
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
                return JSONResponse({"error": "Email giÃ  verificata"}, status_code=400)
            
            if user.confirmation_code != code:
                logger.warning(f"âŒ Invalid code for {email}")
                return JSONResponse({"error": "Codice non valido"}, status_code=400)
            
            user.confirmed = 1
            user.confirmation_code = None
            session.add(user)
            session.commit()
            
            request.session["user_id"] = user.id
            request.session["user_email"] = user.email
            request.session["user_nome"] = user.nome or "User"
            
            logger.info(f"âœ… Email verified for: {email}")
            
            return JSONResponse({
                "message": "Email verificata con successo!",
                "redirect_url": "/profile"
            }, status_code=200)
    
    except Exception as e:
        logger.error(f"Error during verification: {e}", exc_info=True)
        return JSONResponse({"error": "Errore durante la verifica"}, status_code=500)

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Pagina di login"""
    return request.app.state.templates.TemplateResponse(
        "login.html",
        {"request": request}
    )

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
                return JSONResponse({"error": "Email giÃ  verificata"}, status_code=400)
            
            code = generate_verification_code()
            user.confirmation_code = code
            session.add(user)
            session.commit()
            
            send_verification_email(email, code, user.nome or "User")
            
            logger.info(f"â™»ï¸ Resent code to {email}")
            
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
    cognome: str = Form(None)  # âœ… AGGIUNGI cognome
):
    """Registrazione con form HTML (redirect)"""
    with get_session() as session:
        existing = session.exec(select(User).where(User.email == email)).first()
        
        if existing:
            return request.app.state.templates.TemplateResponse(
                "register.html",
                {"request": request, "error": "Email giÃ  registrata"}
            )
        
        password_hash = hashlib.md5(password.encode()).hexdigest()
        
        # âœ… AGGIUNGI cognome
        new_user = User(
            email=email,
            password_md5=password_hash,
            nome=nome,
            cognome=cognome,  # âœ… AGGIUNGI questo
            confirmed=0,
        )
        
        session.add(new_user)
        session.commit()
        
        logger.info(f"âœ… New user registered (HTML): {email}")
        
        return RedirectResponse("/login?registered=true", status_code=302)

@router.get("/logout")
async def logout(request: Request):
    """Logout utente"""
    request.session.clear()
    return RedirectResponse("/", status_code=302)


# ========== RESET PASSWORD ROUTES ==========

@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request):
    """Pagina reset password"""
    return request.app.state.templates.TemplateResponse(
        "reset_password.html",
        {"request": request}
    )

@router.post("/api/request-password-reset")
async def request_password_reset(
    request: Request,
    email: str = Form(...)
):
    """API: richiedi reset password (invia codice via email)"""
    try:
        with get_session() as session:
            user = session.exec(select(User).where(User.email == email)).first()
            
            if not user:
                return JSONResponse({"error": "Email non trovata"}, status_code=404)
            
            # Genera codice reset (6 cifre)
            reset_code = generate_verification_code()  # Usa stessa funzione di verifica
            
            # Salva codice in sessione
            request.session['reset_code'] = reset_code
            request.session['reset_email'] = email
            request.session['reset_timestamp'] = int(time.time())
            
            # Invia email con codice
            send_reset_password_email(email, user.nome or "Utente", reset_code)
            
            logger.info(f"ðŸ” Reset password requested for: {email} - Code: {reset_code}")
            
            return JSONResponse({
                "success": True,
                "message": "Codice inviato via email"
            }, status_code=200)
    
    except Exception as e:
        logger.error(f"Error requesting password reset: {e}", exc_info=True)
        return JSONResponse({"error": "Errore. Riprova."}, status_code=500)

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


@router.post("/api/reset-password")
async def reset_password(
    request: Request,
    email: str = Form(...),
    code: str = Form(...),
    new_password: str = Form(...)
):
    """API: reset password con codice"""
    try:
        # Verifica codice in sessione
        if 'reset_code' not in request.session or 'reset_email' not in request.session:
            return JSONResponse({"error": "Codice non trovato. Richiedi un nuovo reset."}, status_code=400)
        
        # Verifica email
        if request.session['reset_email'] != email:
            return JSONResponse({"error": "Email non corrisponde"}, status_code=400)
        
        # Verifica codice
        if request.session['reset_code'] != code:
            logger.warning(f"âŒ Invalid reset code for {email}")
            return JSONResponse({"error": "Codice non valido"}, status_code=400)
        
        # Verifica timestamp (codice valido 10 minuti = 600 secondi)
        reset_time = request.session.get('reset_timestamp', 0)
        if int(time.time()) - reset_time > 600:
            return JSONResponse({"error": "Codice scaduto. Richiedi un nuovo reset."}, status_code=400)
        
        # Hash nuova password
        new_password_hash = hashlib.md5(new_password.encode()).hexdigest()
        
        # Aggiorna password nel database
        with get_session() as session:
            user = session.exec(select(User).where(User.email == email)).first()
            
            if not user:
                return JSONResponse({"error": "Utente non trovato"}, status_code=404)
            
            user.password_md5 = new_password_hash
            session.add(user)
            session.commit()
            
            logger.info(f"âœ… Password reset successful for: {email}")
        
        # Pulisci sessione
        request.session.pop('reset_code', None)
        request.session.pop('reset_email', None)
        request.session.pop('reset_timestamp', None)
        
        return JSONResponse({
            "success": True,
            "message": "Password reimpostata con successo!"
        }, status_code=200)
    
    except Exception as e:
        logger.error(f"Error resetting password: {e}", exc_info=True)
        return JSONResponse({"error": "Errore. Riprova."}, status_code=500)

# ========== FUNZIONE EMAIL RESET PASSWORD ==========

def send_reset_password_email(email: str, nome: str, reset_code: str) -> bool:
    """Invia email con codice reset password"""
    # âœ… Usa la funzione esistente (adattala al tuo caso)
    from app.utils.email import send_verification_email  # O il nome corretto
    
    subject = "ðŸ” Reset Password - Ispiramy"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; background: #f4f4f4; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; margin-bottom: 32px; }}
            .header h1 {{ color: #667eea; margin: 0; }}
            .code {{ font-size: 42px; font-weight: bold; color: #667eea; text-align: center; letter-spacing: 8px; margin: 32px 0; padding: 20px; background: #f0f4ff; border-radius: 8px; }}
            .footer {{ text-align: center; margin-top: 32px; font-size: 14px; color: #888; }}
            .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 16px; margin: 20px 0; border-radius: 4px; color: #856404; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>ðŸ” Reset Password</h1>
                <p style="color: #666; font-size: 16px;">Ciao {nome},</p>
                <p style="color: #666;">Hai richiesto di reimpostare la tua password su Ispiramy.</p>
            </div>
            
            <p style="text-align: center; font-size: 16px; margin-bottom: 8px; color: #333;">
                Il tuo codice di verifica Ã¨:
            </p>
            
            <div class="code">{reset_code}</div>
            
            <div class="warning">
                <strong>âš ï¸ Importante:</strong> Questo codice Ã¨ valido per <strong>10 minuti</strong>.
            </div>
            
            <p style="text-align: center; margin-top: 32px; color: #666;">
                Se non hai richiesto questo reset, ignora questa email.
            </p>
            
            <div class="footer">
                <p>Â© 2025 Ispiramy - Get Advice from People Who Can Help</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        # âœ… Usa la funzione esistente (adatta i parametri)
        send_verification_email(email, nome, reset_code)
        logger.info(f"âœ… Reset password email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"âŒ Failed to send reset email to {email}: {e}")
        return False

def send_verification_email(to_email: str, code: str, nome: str = "User") -> bool:
    """
    Invia email di verifica usando SendGrid API (HTTP).
    
    Args:
        to_email: Email destinatario
        code: Codice verifica 6 cifre
        nome: Nome utente
    
    Returns:
        bool: True se email inviata con successo
    """
    logger.info("=" * 80)
    logger.info("ðŸ“§ INVIO EMAIL VIA SENDGRID API")
    logger.info("=" * 80)
    
    try:
        # ========== STEP 1: Carica API Key ==========
        api_key = os.getenv('SENDGRID_API_KEY') or os.getenv('SMTP_PASSWORD')
        from_email = os.getenv('FROM_EMAIL', 'noreply@ispiramy.com')
        
        logger.info("ðŸ“‹ STEP 1: Configurazione caricata")
        logger.info(f"   â”œâ”€ API_KEY: {'âœ… SET' if api_key else 'âŒ NOT SET'}")
        logger.info(f"   â”œâ”€ FROM_EMAIL: {from_email}")
        logger.info(f"   â”œâ”€ TO_EMAIL: {to_email}")
        logger.info(f"   â””â”€ NOME: {nome}")
        
        from app.utils.email_backend import is_backend_available
        if not is_backend_available():
            logger.error("Nessun backend email disponibile (RESEND_API_KEY / SENDGRID_API_KEY mancanti)")
            return False
        
        # ========== STEP 2: Costruisci messaggio HTML ==========
        logger.info("ðŸ“ STEP 2: Costruzione messaggio...")
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 40px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                h1 {{ color: #667eea; margin-bottom: 20px; }}
                .code {{ font-size: 32px; font-weight: bold; color: #667eea; background: #f0f4ff; padding: 20px; border-radius: 8px; text-align: center; margin: 30px 0; letter-spacing: 4px; }}
                p {{ color: #555; line-height: 1.6; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #888; font-size: 0.9rem; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>ðŸ¦Š Benvenuto su Ispiramy, {nome}!</h1>
                <p>Grazie per esserti registrato. Ecco il tuo codice di verifica:</p>
                <div class="code">{code}</div>
                <p>Inserisci questo codice nella pagina di registrazione per completare la verifica del tuo account.</p>
                <p><strong>Importante:</strong> Questo codice Ã¨ valido per 10 minuti.</p>
                <div class="footer">
                    <p>Se non hai richiesto questa email, ignorala.<br>Â© 2025 Ispiramy - Tutti i diritti riservati</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # ========== STEP 3: Crea messaggio SendGrid ==========
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject='Codice di Verifica Ispiramy',
            html_content=html_content
        )
        
        logger.info("âœ… STEP 2: Messaggio costruito")
        logger.info(f"   â”œâ”€ Subject: Codice di Verifica Ispiramy")
        logger.info(f"   â”œâ”€ From: {from_email}")
        logger.info(f"   â”œâ”€ To: {to_email}")
        logger.info(f"   â””â”€ Codice: {code}")
        
        # ========== STEP 4: Invia via API ==========
        logger.info("ðŸ“¤ STEP 3: Invio via SendGrid API...")
        
        try:
            from app.utils.email_backend import mail_send
            response = mail_send(api_key, message)
            
            logger.info(f"âœ… STEP 3: Email inviata!")
            logger.info(f"   â”œâ”€ Status Code: {response.status_code}")
            logger.info(f"   â”œâ”€ Headers: {dict(response.headers)}")
            logger.info(f"   â””â”€ Body: {response.body}")
            
            logger.info("=" * 80)
            logger.info("ðŸŽ‰ EMAIL INVIATA CON SUCCESSO!")
            logger.info("=" * 80)
            
            return True
        
        except Exception as e:
            logger.error(f"âŒ STEP 3: Errore SendGrid API: {type(e).__name__}")
            logger.error(f"   Messaggio: {str(e)}")
            
            # Log dettagli errore SendGrid
            if hasattr(e, 'body'):
                logger.error(f"   Body: {e.body}")
            if hasattr(e, 'to_dict'):
                logger.error(f"   Details: {e.to_dict}")
            
            return False
    
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"âŒ ERRORE FATALE INVIO EMAIL")
        logger.error(f"   Tipo: {type(e).__name__}")
        logger.error(f"   Messaggio: {e}")
        logger.error("=" * 80)
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return False

# ========== ORA PUOI USARE LA FUNZIONE ==========

# ...existing code (verify_token, login, etc)...

@router.post("/api/register")
async def api_register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    nome: str = Form(...),
    cognome: str = Form(None)
):
    """API Registrazione con invio email di conferma"""
    try:
        with get_session() as session:
            existing = session.exec(select(User).where(User.email == email)).first()
            
            if existing:
                if existing.confirmed == 1:
                    logger.warning(f"âŒ Registration attempt with existing email: {email}")
                    return JSONResponse({
                        "error": "Email giÃ  registrata",
                        "message": "Questa email Ã¨ giÃ  registrata. Hai giÃ  un account?",
                        "redirect_url": "/login",
                        "show_login_link": True
                    }, status_code=400)
                else:
                    code = generate_verification_code()
                    existing.confirmation_code = code
                    session.add(existing)
                    session.commit()
                    
                    # âœ… Ora funziona con 3 parametri
                    send_verification_email(email, code, existing.nome or "User")
                    
                    logger.info(f"â™»ï¸ Resent confirmation code to: {email}")
                    
                    return JSONResponse({
                        "message": "Codice di verifica inviato nuovamente!",
                        "email": email,
                        "requires_verification": True
                    }, status_code=200)
            
            password_hash = hashlib.md5(password.encode()).hexdigest()
            code = generate_verification_code()
            
            new_user = User(
                email=email,
                password_md5=password_hash,
                nome=nome,
                cognome=cognome,
                confirmed=0,
                confirmation_code=code
            )
            
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            
            # âœ… Ora funziona con 3 parametri
            email_sent = send_verification_email(email, code, nome)
            
            if not email_sent:
                logger.warning(f"âš ï¸ User registered but email failed: {email}")
            
            logger.info(f"âœ… New user registered: {email} (ID: {new_user.id}) - Code: {code}")
            
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
                return JSONResponse({"error": "Email giÃ  verificata"}, status_code=400)
            
            if user.confirmation_code != code:
                logger.warning(f"âŒ Invalid code for {email}")
                return JSONResponse({"error": "Codice non valido"}, status_code=400)
            
            user.confirmed = 1
            user.confirmation_code = None
            session.add(user)
            session.commit()
            
            request.session["user_id"] = user.id
            request.session["user_email"] = user.email
            request.session["user_nome"] = user.nome or "User"
            
            logger.info(f"âœ… Email verified for: {email}")
            
            return JSONResponse({
                "message": "Email verificata con successo!",
                "redirect_url": "/profile"
            }, status_code=200)
    
    except Exception as e:
        logger.error(f"Error during verification: {e}", exc_info=True)
        return JSONResponse({"error": "Errore durante la verifica"}, status_code=500)

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Pagina di login"""
    return request.app.state.templates.TemplateResponse(
        "login.html",
        {"request": request}
    )

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
                return JSONResponse({"error": "Email giÃ  verificata"}, status_code=400)
            
            code = generate_verification_code()
            user.confirmation_code = code
            session.add(user)
            session.commit()
            
            send_verification_email(email, code, user.nome or "User")
            
            logger.info(f"â™»ï¸ Resent code to {email}")
            
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
    cognome: str = Form(None)  # âœ… AGGIUNGI cognome
):
    """Registrazione con form HTML (redirect)"""
    with get_session() as session:
        existing = session.exec(select(User).where(User.email == email)).first()
        
        if existing:
            return request.app.state.templates.TemplateResponse(
                "register.html",
                {"request": request, "error": "Email giÃ  registrata"}
            )
        
        password_hash = hashlib.md5(password.encode()).hexdigest()
        
        # âœ… AGGIUNGI cognome
        new_user = User(
            email=email,
            password_md5=password_hash,
            nome=nome,
            cognome=cognome,  # âœ… AGGIUNGI questo
            confirmed=0,
        )
        
        session.add(new_user)
        session.commit()
        
        logger.info(f"âœ… New user registered (HTML): {email}")
        
        return RedirectResponse("/login?registered=true", status_code=302)

@router.get("/logout")
async def logout(request: Request):
    """Logout utente"""
    request.session.clear()
    return RedirectResponse("/", status_code=302)


# ========== RESET PASSWORD ROUTES ==========

@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request):
    """Pagina reset password"""
    return request.app.state.templates.TemplateResponse(
        "reset_password.html",
        {"request": request}
    )

@router.post("/api/request-password-reset")
async def request_password_reset(
    request: Request,
    email: str = Form(...)
):
    """API: richiedi reset password (invia codice via email)"""
    try:
        with get_session() as session:
            user = session.exec(select(User).where(User.email == email)).first()
            
            if not user:
                return JSONResponse({"error": "Email non trovata"}, status_code=404)
            
            # Genera codice reset (6 cifre)
            reset_code = generate_verification_code()  # Usa stessa funzione di verifica
            
            # Salva codice in sessione
            request.session['reset_code'] = reset_code
            request.session['reset_email'] = email
            request.session['reset_timestamp'] = int(time.time())
            
            # Invia email con codice
            send_reset_password_email(email, user.nome or "Utente", reset_code)
            
            logger.info(f"ðŸ” Reset password requested for: {email} - Code: {reset_code}")
            
            return JSONResponse({
                "success": True,
                "message": "Codice inviato via email"
            }, status_code=200)
    
    except Exception as e:
        logger.error(f"Error requesting password reset: {e}", exc_info=True)
        return JSONResponse({"error": "Errore. Riprova."}, status_code=500)

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


@router.post("/api/reset-password")
async def reset_password(
    request: Request,
    email: str = Form(...),
    code: str = Form(...),
    new_password: str = Form(...)
):
    """API: reset password con codice"""
    try:
        # Verifica codice in sessione
        if 'reset_code' not in request.session or 'reset_email' not in request.session:
            return JSONResponse({"error": "Codice non trovato. Richiedi un nuovo reset."}, status_code=400)
        
        # Verifica email
        if request.session['reset_email'] != email:
            return JSONResponse({"error": "Email non corrisponde"}, status_code=400)
        
        # Verifica codice
        if request.session['reset_code'] != code:
            logger.warning(f"âŒ Invalid reset code for {email}")
            return JSONResponse({"error": "Codice non valido"}, status_code=400)
        
        # Verifica timestamp (codice valido 10 minuti = 600 secondi)
        reset_time = request.session.get('reset_timestamp', 0)
        if int(time.time()) - reset_time > 600:
            return JSONResponse({"error": "Codice scaduto. Richiedi un nuovo reset."}, status_code=400)
        
        # Hash nuova password
        new_password_hash = hashlib.md5(new_password.encode()).hexdigest()
        
        # Aggiorna password nel database
        with get_session() as session:
            user = session.exec(select(User).where(User.email == email)).first()
            
            if not user:
                return JSONResponse({"error": "Utente non trovato"}, status_code=404)
            
            user.password_md5 = new_password_hash
            session.add(user)
            session.commit()
            
            logger.info(f"âœ… Password reset successful for: {email}")
        
        # Pulisci sessione
        request.session.pop('reset_code', None)
        request.session.pop('reset_email', None)
        request.session.pop('reset_timestamp', None)
        
        return JSONResponse({
            "success": True,
            "message": "Password reimpostata con successo!"
        }, status_code=200)
    
    except Exception as e:
        logger.error(f"Error resetting password: {e}", exc_info=True)
        return JSONResponse({"error": "Errore. Riprova."}, status_code=500)

# ========== FUNZIONE EMAIL RESET PASSWORD ==========

def send_reset_password_email(email: str, nome: str, reset_code: str) -> bool:
    """Invia email con codice reset password"""
    # âœ… Usa la funzione esistente (adattala al tuo caso)
    from app.utils.email import send_verification_email  # O il nome corretto
    
    subject = "ðŸ” Reset Password - Ispiramy"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; background: #f4f4f4; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; margin-bottom: 32px; }}
            .header h1 {{ color: #667eea; margin: 0; }}
            .code {{ font-size: 42px; font-weight: bold; color: #667eea; text-align: center; letter-spacing: 8px; margin: 32px 0; padding: 20px; background: #f0f4ff; border-radius: 8px; }}
            .footer {{ text-align: center; margin-top: 32px; font-size: 14px; color: #888; }}
            .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 16px; margin: 20px 0; border-radius: 4px; color: #856404; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>ðŸ” Reset Password</h1>
                <p style="color: #666; font-size: 16px;">Ciao {nome},</p>
                <p style="color: #666;">Hai richiesto di reimpostare la tua password su Ispiramy.</p>
            </div>
            
            <p style="text-align: center; font-size: 16px; margin-bottom: 8px; color: #333;">
                Il tuo codice di verifica Ã¨:
            </p>
            
            <div class="code">{reset_code}</div>
            
            <div class="warning">
                <strong>âš ï¸ Importante:</strong> Questo codice Ã¨ valido per <strong>10 minuti</strong>.
            </div>
            
            <p style="text-align: center; margin-top: 32px; color: #666;">
                Se non hai richiesto questo reset, ignora questa email.
            </p>
            
            <div class="footer">
                <p>Â© 2025 Ispiramy - Get Advice from People Who Can Help</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        # âœ… Usa la funzione esistente (adatta i parametri)
        send_verification_email(email, nome, reset_code)
        logger.info(f"âœ… Reset password email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"âŒ Failed to send reset email to {email}: {e}")
        return False

def send_verification_email(to_email: str, code: str, nome: str = "User") -> bool:
    """
    Invia email di verifica usando SendGrid API (HTTP).
    
    Args:
        to_email: Email destinatario
        code: Codice verifica 6 cifre
        nome: Nome utente
    
    Returns:
        bool: True se email inviata con successo
    """
    logger.info("=" * 80)
    logger.info("ðŸ“§ INVIO EMAIL VIA SENDGRID API")
    logger.info("=" * 80)
    
    try:
        # ========== STEP 1: Carica API Key ==========
        api_key = os.getenv('SENDGRID_API_KEY') or os.getenv('SMTP_PASSWORD')
        from_email = os.getenv('FROM_EMAIL', 'noreply@ispiramy.com')
        
        logger.info("ðŸ“‹ STEP 1: Configurazione caricata")
        logger.info(f"   â”œâ”€ API_KEY: {'âœ… SET' if api_key else 'âŒ NOT SET'}")
        logger.info(f"   â”œâ”€ FROM_EMAIL: {from_email}")
        logger.info(f"   â”œâ”€ TO_EMAIL: {to_email}")
        logger.info(f"   â””â”€ NOME: {nome}")
        
        from app.utils.email_backend import is_backend_available
        if not is_backend_available():
            logger.error("Nessun backend email disponibile (RESEND_API_KEY / SENDGRID_API_KEY mancanti)")
            return False
        
        # ========== STEP 2: Costruisci messaggio HTML ==========
        logger.info("ðŸ“ STEP 2: Costruzione messaggio...")
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 40px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                h1 {{ color: #667eea; margin-bottom: 20px; }}
                .code {{ font-size: 32px; font-weight: bold; color: #667eea; background: #f0f4ff; padding: 20px; border-radius: 8px; text-align: center; margin: 30px 0; letter-spacing: 4px; }}
                p {{ color: #555; line-height: 1.6; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #888; font-size: 0.9rem; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>ðŸ¦Š Benvenuto su Ispiramy, {nome}!</h1>
                <p>Grazie per esserti registrato. Ecco il tuo codice di verifica:</p>
                <div class="code">{code}</div>
                <p>Inserisci questo codice nella pagina di registrazione per completare la verifica del tuo account.</p>
                <p><strong>Importante:</strong> Questo codice Ã¨ valido per 10 minuti.</p>
                <div class="footer">
                    <p>Se non hai richiesto questa email, ignorala.<br>Â© 2025 Ispiramy - Tutti i diritti riservati</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # ========== STEP 3: Crea messaggio SendGrid ==========
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject='Codice di Verifica Ispiramy',
            html_content=html_content
        )
        
        logger.info("âœ… STEP 2: Messaggio costruito")
        logger.info(f"   â”œâ”€ Subject: Codice di Verifica Ispiramy")
        logger.info(f"   â”œâ”€ From: {from_email}")
        logger.info(f"   â”œâ”€ To: {to_email}")
        logger.info(f"   â””â”€ Codice: {code}")
        
        # ========== STEP 4: Invia via API ==========
        logger.info("ðŸ“¤ STEP 3: Invio via SendGrid API...")
        
        try:
            from app.utils.email_backend import mail_send
            response = mail_send(api_key, message)
            
            logger.info(f"âœ… STEP 3: Email inviata!")
            logger.info(f"   â”œâ”€ Status Code: {response.status_code}")
            logger.info(f"   â”œâ”€ Headers: {dict(response.headers)}")
            logger.info(f"   â””â”€ Body: {response.body}")
            
            logger.info("=" * 80)
            logger.info("ðŸŽ‰ EMAIL INVIATA CON SUCCESSO!")
            logger.info("=" * 80)
            
            return True
        
        except Exception as e:
            logger.error(f"âŒ STEP 3: Errore SendGrid API: {type(e).__name__}")
            logger.error(f"   Messaggio: {str(e)}")
            
            # Log dettagli errore SendGrid
            if hasattr(e, 'body'):
                logger.error(f"   Body: {e.body}")
            if hasattr(e, 'to_dict'):
                logger.error(f"   Details: {e.to_dict}")
            
            return False
    
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"âŒ ERRORE FATALE INVIO EMAIL")
        logger.error(f"   Tipo: {type(e).__name__}")
        logger.error(f"   Messaggio: {e}")
        logger.error("=" * 80)
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return False
