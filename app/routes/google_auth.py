"""
Google OAuth2 Login Route
Gestisce il login/registrazione tramite account Google
"""
import os

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from sqlmodel import select

from app.database import get_session
from app.models import User
from app.utils.password import UNUSABLE_PASSWORD
from app.logger_config import logger

import jwt
from datetime import datetime, timedelta

router = APIRouter()

# Configurazione OAuth
oauth = OAuth()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    logger.info("✅ Google OAuth configurato correttamente")
else:
    logger.warning("⚠️ Google OAuth non configurato: GOOGLE_CLIENT_ID o GOOGLE_CLIENT_SECRET mancanti")


@router.get("/auth/google")
async def google_login(request: Request):
    """Redirect a Google per il login OAuth"""
    if not GOOGLE_CLIENT_ID:
        return RedirectResponse("/login", status_code=302)
    
    # Costruisci redirect_uri dinamicamente in base all'host della richiesta
    redirect_uri = str(request.url_for("google_callback"))
    
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/google/callback")
async def google_callback(request: Request):
    """Callback da Google dopo il consenso dell'utente"""
    try:
        token = await oauth.google.authorize_access_token(request)
        userinfo = token.get("userinfo")
        
        if not userinfo:
            logger.error("❌ Google OAuth: nessuna userinfo nel token")
            return RedirectResponse("/login", status_code=302)
        
        google_id = userinfo.get("sub")
        email = userinfo.get("email")
        nome = userinfo.get("given_name", "")
        cognome = userinfo.get("family_name", "")
        
        if not email or not google_id:
            logger.error("❌ Google OAuth: email o sub mancanti nella risposta")
            return RedirectResponse("/login", status_code=302)

        # Senza email_verified il collegamento per email qui sotto diventa un
        # takeover: basterebbe un account Google con l'indirizzo della vittima
        # non verificato per entrare nel suo account Ispiramy.
        if userinfo.get("email_verified") is False:
            logger.warning(f"⚠️ Google OAuth: email non verificata da Google ({email}), login rifiutato")
            return RedirectResponse("/login?error=email_non_verificata", status_code=302)

        logger.info(f"🔑 Google OAuth callback per: {email} (sub: {google_id})")
        
        with get_session() as session:
            # 1. Cerca utente per google_id
            user = session.exec(
                select(User).where(User.google_id == google_id)
            ).first()
            
            if user:
                # Utente già collegato con Google → login
                logger.info(f"✅ Google login per utente esistente: {user.email} (ID: {user.id})")
                _set_session(request, session, user)
                return RedirectResponse("/profile", status_code=302)
            
            # 2. Cerca utente per email (account già registrato con email/password)
            user = session.exec(
                select(User).where(User.email == email)
            ).first()
            
            if user:
                # Collega account Google all'utente esistente
                user.google_id = google_id
                if not user.nome and nome:
                    user.nome = nome
                if not user.cognome and cognome:
                    user.cognome = cognome
                session.add(user)
                session.commit()
                session.refresh(user)
                
                logger.info(f"🔗 Account Google collegato a utente esistente: {user.email} (ID: {user.id})")
                _set_session(request, session, user)
                return RedirectResponse("/profile", status_code=302)
            
            # 3. Nuovo utente → crea account.
            # Nessuna password: l'accesso avviene via Google. Il campo resta
            # valorizzato con un valore impossibile da indovinare, cosi' non
            # esiste una password "vera" da rubare. Per accedere anche con
            # email e password l'utente usa "password dimenticata".
            password_hash = UNUSABLE_PASSWORD
            
            new_user = User(
                email=email,
                password_md5=password_hash,
                nome=nome or None,
                cognome=cognome or None,
                google_id=google_id,
                confirmed=1,  # Email già verificata da Google
            )
            
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            
            logger.info(f"✅ Nuovo utente registrato via Google: {email} (ID: {new_user.id})")
            _set_session(request, session, new_user)
            return RedirectResponse("/profile", status_code=302)
    
    except Exception as e:
        logger.error(f"❌ Errore Google OAuth callback: {e}", exc_info=True)
        return RedirectResponse("/login", status_code=302)


def _set_session(request: Request, session, user: User):
    """Imposta la sessione con JWT e dati utente"""
    JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
    token_data = {
        "user_id": user.id,
        "email": user.email,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    access_token = jwt.encode(token_data, JWT_SECRET, algorithm="HS256")
    
    request.session["access_token"] = access_token
    request.session["user_id"] = user.id
    request.session["user_email"] = user.email
    request.session["user_nome"] = user.nome or "User"
