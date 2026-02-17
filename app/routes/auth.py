from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.database import get_session
from app.models import User
from sqlmodel import select
import time
import hashlib
from typing import Optional
from app.logger_config import logger
from app.utils.email import generate_verification_code  # ✅ RIMUOVI send_verification_email da qui
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

def verify_token(request: Request) -> Optional[User]:
    """
    Verifica token JWT e restituisce utente autenticato
    """
    try:
        # ✅ Leggi token dalla sessione
        token = request.session.get("access_token")
        
        if not token:
            logger.warning("⚠️ No access_token in session")
            logger.debug(f"Session keys: {list(request.session.keys())}")
            
            # Fallback: controlla se c'è user_id nella sessione (sessione senza JWT)
            user_id = request.session.get("user_id")
            if user_id:
                logger.info(f"🔄 Fallback: Found user_id in session: {user_id}")
                with get_session() as session:
                    user = session.get(User, user_id)
                    if user:
                        return user
            
            return None
        
        # Decodifica JWT
        JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            user_id = payload.get("user_id")
            
            if not user_id:
                logger.warning("⚠️ No user_id in token payload")
                return None
        
        except jwt.ExpiredSignatureError:
            logger.warning("⚠️ Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"⚠️ Invalid token: {str(e)}")
            return None
        
        # ✅ Ottieni utente dal database
        with get_session() as session:
            user = session.get(User, user_id)
            
            if not user:
                logger.warning(f"⚠️ User {user_id} not found in database")
                return None
            
            return user
    
    except Exception as e:
        logger.error(f"Error verifying token: {str(e)}", exc_info=True)
        return None

# Alias per compatibilità
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
        
        logger.info(f"✅ User logged in: {user.email}")
        
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
            
            # ✅ Genera token JWT
            JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
            token_data = {
                "user_id": user.id,
                "email": user.email,
                "exp": datetime.utcnow() + timedelta(days=7)
            }
            access_token = jwt.encode(token_data, JWT_SECRET, algorithm="HS256")
            
            # ✅ SALVA TOKEN IN SESSION (IMPORTANTE!)
            request.session["access_token"] = access_token
            request.session["user_id"] = user.id
            request.session["user_email"] = user.email
            request.session["user_nome"] = user.nome
            
            logger.info(f"✅ User logged in: {user.nome} ({user.email})")
            logger.info(f"🔑 Session data: {request.session}")  # Debug
            
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
        logger.error(f"Login error: {str(e)}", exc_info=True)
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
                    
                    # ✅ Ora funziona con 3 parametri
                    send_verification_email(email, code, existing.nome or "User")
                    
                    logger.info(f"♻️ Resent confirmation code to: {email}")
                    
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
                bollini=0,
                confirmation_code=code
            )
            
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            
            # ✅ Ora funziona con 3 parametri
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
            
            logger.info(f"🔐 Reset password requested for: {email} - Code: {reset_code}")
            
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
            logger.warning(f"❌ Invalid reset code for {email}")
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
            
            logger.info(f"✅ Password reset successful for: {email}")
        
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
    # ✅ Usa la funzione esistente (adattala al tuo caso)
    from app.utils.email import send_verification_email  # O il nome corretto
    
    subject = "🔐 Reset Password - Helpy"
    
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
                <h1>🔐 Reset Password</h1>
                <p style="color: #666; font-size: 16px;">Ciao {nome},</p>
                <p style="color: #666;">Hai richiesto di reimpostare la tua password su Helpy.</p>
            </div>
            
            <p style="text-align: center; font-size: 16px; margin-bottom: 8px; color: #333;">
                Il tuo codice di verifica è:
            </p>
            
            <div class="code">{reset_code}</div>
            
            <div class="warning">
                <strong>⚠️ Importante:</strong> Questo codice è valido per <strong>10 minuti</strong>.
            </div>
            
            <p style="text-align: center; margin-top: 32px; color: #666;">
                Se non hai richiesto questo reset, ignora questa email.
            </p>
            
            <div class="footer">
                <p>© 2025 Helpy - Get Advice from People Who Can Help</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        # ✅ Usa la funzione esistente (adatta i parametri)
        send_verification_email(email, nome, reset_code)
        logger.info(f"✅ Reset password email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send reset email to {email}: {e}")
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
    logger.info("📧 INVIO EMAIL VIA SENDGRID API")
    logger.info("=" * 80)
    
    try:
        # ========== STEP 1: Carica API Key ==========
        api_key = os.getenv('SENDGRID_API_KEY') or os.getenv('SMTP_PASSWORD')
        from_email = os.getenv('FROM_EMAIL', 'noreply@helpy.com')
        
        logger.info("📋 STEP 1: Configurazione caricata")
        logger.info(f"   ├─ API_KEY: {'✅ SET' if api_key else '❌ NOT SET'}")
        logger.info(f"   ├─ FROM_EMAIL: {from_email}")
        logger.info(f"   ├─ TO_EMAIL: {to_email}")
        logger.info(f"   └─ NOME: {nome}")
        
        if not api_key:
            logger.error("❌ SENDGRID_API_KEY non configurata!")
            return False
        
        # ========== STEP 2: Costruisci messaggio HTML ==========
        logger.info("📝 STEP 2: Costruzione messaggio...")
        
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
                <h1>🦊 Benvenuto su Helpy, {nome}!</h1>
                <p>Grazie per esserti registrato. Ecco il tuo codice di verifica:</p>
                <div class="code">{code}</div>
                <p>Inserisci questo codice nella pagina di registrazione per completare la verifica del tuo account.</p>
                <p><strong>Importante:</strong> Questo codice è valido per 10 minuti.</p>
                <div class="footer">
                    <p>Se non hai richiesto questa email, ignorala.<br>© 2025 Helpy - Tutti i diritti riservati</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # ========== STEP 3: Crea messaggio SendGrid ==========
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject='Codice di Verifica Helpy',
            html_content=html_content
        )
        
        logger.info("✅ STEP 2: Messaggio costruito")
        logger.info(f"   ├─ Subject: Codice di Verifica Helpy")
        logger.info(f"   ├─ From: {from_email}")
        logger.info(f"   ├─ To: {to_email}")
        logger.info(f"   └─ Codice: {code}")
        
        # ========== STEP 4: Invia via API ==========
        logger.info("📤 STEP 3: Invio via SendGrid API...")
        
        try:
            sg = SendGridAPIClient(api_key)
            response = sg.send(message)
            
            logger.info(f"✅ STEP 3: Email inviata!")
            logger.info(f"   ├─ Status Code: {response.status_code}")
            logger.info(f"   ├─ Headers: {dict(response.headers)}")
            logger.info(f"   └─ Body: {response.body}")
            
            logger.info("=" * 80)
            logger.info("🎉 EMAIL INVIATA CON SUCCESSO!")
            logger.info("=" * 80)
            
            return True
        
        except Exception as e:
            logger.error(f"❌ STEP 3: Errore SendGrid API: {type(e).__name__}")
            logger.error(f"   Messaggio: {str(e)}")
            
            # Log dettagli errore SendGrid
            if hasattr(e, 'body'):
                logger.error(f"   Body: {e.body}")
            if hasattr(e, 'to_dict'):
                logger.error(f"   Details: {e.to_dict}")
            
            return False
    
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ ERRORE FATALE INVIO EMAIL")
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
                    
                    # ✅ Ora funziona con 3 parametri
                    send_verification_email(email, code, existing.nome or "User")
                    
                    logger.info(f"♻️ Resent confirmation code to: {email}")
                    
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
                bollini=0,
                confirmation_code=code
            )
            
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            
            # ✅ Ora funziona con 3 parametri
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
            
            logger.info(f"🔐 Reset password requested for: {email} - Code: {reset_code}")
            
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
            logger.warning(f"❌ Invalid reset code for {email}")
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
            
            logger.info(f"✅ Password reset successful for: {email}")
        
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
    # ✅ Usa la funzione esistente (adattala al tuo caso)
    from app.utils.email import send_verification_email  # O il nome corretto
    
    subject = "🔐 Reset Password - Helpy"
    
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
                <h1>🔐 Reset Password</h1>
                <p style="color: #666; font-size: 16px;">Ciao {nome},</p>
                <p style="color: #666;">Hai richiesto di reimpostare la tua password su Helpy.</p>
            </div>
            
            <p style="text-align: center; font-size: 16px; margin-bottom: 8px; color: #333;">
                Il tuo codice di verifica è:
            </p>
            
            <div class="code">{reset_code}</div>
            
            <div class="warning">
                <strong>⚠️ Importante:</strong> Questo codice è valido per <strong>10 minuti</strong>.
            </div>
            
            <p style="text-align: center; margin-top: 32px; color: #666;">
                Se non hai richiesto questo reset, ignora questa email.
            </p>
            
            <div class="footer">
                <p>© 2025 Helpy - Get Advice from People Who Can Help</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        # ✅ Usa la funzione esistente (adatta i parametri)
        send_verification_email(email, nome, reset_code)
        logger.info(f"✅ Reset password email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send reset email to {email}: {e}")
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
    logger.info("📧 INVIO EMAIL VIA SENDGRID API")
    logger.info("=" * 80)
    
    try:
        # ========== STEP 1: Carica API Key ==========
        api_key = os.getenv('SENDGRID_API_KEY') or os.getenv('SMTP_PASSWORD')
        from_email = os.getenv('FROM_EMAIL', 'noreply@helpy.com')
        
        logger.info("📋 STEP 1: Configurazione caricata")
        logger.info(f"   ├─ API_KEY: {'✅ SET' if api_key else '❌ NOT SET'}")
        logger.info(f"   ├─ FROM_EMAIL: {from_email}")
        logger.info(f"   ├─ TO_EMAIL: {to_email}")
        logger.info(f"   └─ NOME: {nome}")
        
        if not api_key:
            logger.error("❌ SENDGRID_API_KEY non configurata!")
            return False
        
        # ========== STEP 2: Costruisci messaggio HTML ==========
        logger.info("📝 STEP 2: Costruzione messaggio...")
        
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
                <h1>🦊 Benvenuto su Helpy, {nome}!</h1>
                <p>Grazie per esserti registrato. Ecco il tuo codice di verifica:</p>
                <div class="code">{code}</div>
                <p>Inserisci questo codice nella pagina di registrazione per completare la verifica del tuo account.</p>
                <p><strong>Importante:</strong> Questo codice è valido per 10 minuti.</p>
                <div class="footer">
                    <p>Se non hai richiesto questa email, ignorala.<br>© 2025 Helpy - Tutti i diritti riservati</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # ========== STEP 3: Crea messaggio SendGrid ==========
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject='Codice di Verifica Helpy',
            html_content=html_content
        )
        
        logger.info("✅ STEP 2: Messaggio costruito")
        logger.info(f"   ├─ Subject: Codice di Verifica Helpy")
        logger.info(f"   ├─ From: {from_email}")
        logger.info(f"   ├─ To: {to_email}")
        logger.info(f"   └─ Codice: {code}")
        
        # ========== STEP 4: Invia via API ==========
        logger.info("📤 STEP 3: Invio via SendGrid API...")
        
        try:
            sg = SendGridAPIClient(api_key)
            response = sg.send(message)
            
            logger.info(f"✅ STEP 3: Email inviata!")
            logger.info(f"   ├─ Status Code: {response.status_code}")
            logger.info(f"   ├─ Headers: {dict(response.headers)}")
            logger.info(f"   └─ Body: {response.body}")
            
            logger.info("=" * 80)
            logger.info("🎉 EMAIL INVIATA CON SUCCESSO!")
            logger.info("=" * 80)
            
            return True
        
        except Exception as e:
            logger.error(f"❌ STEP 3: Errore SendGrid API: {type(e).__name__}")
            logger.error(f"   Messaggio: {str(e)}")
            
            # Log dettagli errore SendGrid
            if hasattr(e, 'body'):
                logger.error(f"   Body: {e.body}")
            if hasattr(e, 'to_dict'):
                logger.error(f"   Details: {e.to_dict}")
            
            return False
    
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ ERRORE FATALE INVIO EMAIL")
        logger.error(f"   Tipo: {type(e).__name__}")
        logger.error(f"   Messaggio: {e}")
        logger.error("=" * 80)
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return False