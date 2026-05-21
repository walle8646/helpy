"""
Stripe Connect — Onboarding consulenti e gestione account connessi
"""
import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from sqlmodel import Session
from app.database import engine
from app.models import User
from app.routes.auth import verify_token
from app.logger_config import logger

router = APIRouter()

# Lazy import stripe per evitare errori se non installato
def _get_stripe():
    try:
        from app.utils.stripe_config import stripe_module
        if not stripe_module:
            raise RuntimeError("Stripe non configurato")
        return stripe_module
    except Exception as e:
        raise HTTPException(status_code=503, detail="Stripe non disponibile")


@router.post("/api/stripe/connect/onboard")
async def start_onboarding(request: Request):
    """Crea un account Express Stripe e restituisce il link di onboarding"""
    user = verify_token(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    stripe = _get_stripe()
    app_url = os.getenv("BASE_URL", "http://localhost:8080")
    
    with Session(engine) as session:
        db_user = session.get(User, user.id)
        if not db_user:
            raise HTTPException(status_code=404, detail="Utente non trovato")
        
        # Crea account Express se non esiste già
        if not db_user.stripe_account_id:
            try:
                account = stripe.Account.create(
                    type="express",
                    country="IT",
                    email=db_user.email,
                    capabilities={
                        "card_payments": {"requested": True},
                        "transfers": {"requested": True},
                    },
                    metadata={"ispiramy_user_id": str(db_user.id)},
                )
                db_user.stripe_account_id = account.id
                session.add(db_user)
                session.commit()
                logger.info(f"✅ Stripe Connect account creato: {account.id} per user {db_user.id}")
            except Exception as e:
                logger.error(f"❌ Errore creazione account Stripe Connect: {e}")
                raise HTTPException(status_code=500, detail="Errore nella creazione dell'account Stripe")
        
        # Genera Account Link per l'onboarding
        try:
            account_link = stripe.AccountLink.create(
                account=db_user.stripe_account_id,
                refresh_url=f"{app_url}/stripe/connect/refresh",
                return_url=f"{app_url}/stripe/connect/return",
                type="account_onboarding",
            )
            return {"success": True, "url": account_link.url}
        except Exception as e:
            logger.error(f"❌ Errore creazione Account Link: {e}")
            raise HTTPException(status_code=500, detail="Errore nella generazione del link di onboarding")


@router.get("/stripe/connect/return")
async def onboarding_return(request: Request):
    """Callback dopo che il consulente completa l'onboarding Stripe"""
    user = verify_token(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    
    stripe = _get_stripe()
    
    with Session(engine) as session:
        db_user = session.get(User, user.id)
        if db_user and db_user.stripe_account_id:
            try:
                account = stripe.Account.retrieve(db_user.stripe_account_id)
                if account.charges_enabled and account.payouts_enabled:
                    db_user.stripe_onboarding_complete = True
                    session.add(db_user)
                    session.commit()
                    logger.info(f"✅ Onboarding completato per user {db_user.id}")
            except Exception as e:
                logger.error(f"Errore verifica account Stripe: {e}")
    
    return RedirectResponse("/profile?stripe=success", status_code=302)


@router.get("/stripe/connect/refresh")
async def onboarding_refresh(request: Request):
    """Se il link di onboarding scade, ne genera uno nuovo"""
    user = verify_token(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    
    stripe = _get_stripe()
    app_url = os.getenv("BASE_URL", "http://localhost:8080")
    
    with Session(engine) as session:
        db_user = session.get(User, user.id)
        if not db_user or not db_user.stripe_account_id:
            return RedirectResponse("/profile", status_code=302)
        
        try:
            account_link = stripe.AccountLink.create(
                account=db_user.stripe_account_id,
                refresh_url=f"{app_url}/stripe/connect/refresh",
                return_url=f"{app_url}/stripe/connect/return",
                type="account_onboarding",
            )
            return RedirectResponse(account_link.url, status_code=302)
        except Exception as e:
            logger.error(f"Errore refresh onboarding: {e}")
            return RedirectResponse("/profile?stripe=error", status_code=302)


@router.get("/api/stripe/connect/status")
async def connect_status(request: Request):
    """Restituisce lo stato dell'account Stripe Connect del consulente"""
    user = verify_token(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    stripe = _get_stripe()
    
    with Session(engine) as session:
        db_user = session.get(User, user.id)
        if not db_user:
            raise HTTPException(status_code=404)
        
        if not db_user.stripe_account_id:
            return {
                "connected": False,
                "onboarding_complete": False,
                "charges_enabled": False,
                "payouts_enabled": False,
            }
        
        try:
            account = stripe.Account.retrieve(db_user.stripe_account_id)
            
            # Aggiorna stato onboarding se cambiato
            is_complete = account.charges_enabled and account.payouts_enabled
            if is_complete != db_user.stripe_onboarding_complete:
                db_user.stripe_onboarding_complete = is_complete
                session.add(db_user)
                session.commit()
            
            return {
                "connected": True,
                "onboarding_complete": is_complete,
                "charges_enabled": account.charges_enabled,
                "payouts_enabled": account.payouts_enabled,
                "account_id": db_user.stripe_account_id,
            }
        except Exception as e:
            logger.error(f"Errore recupero stato account: {e}")
            return {
                "connected": True,
                "onboarding_complete": db_user.stripe_onboarding_complete,
                "charges_enabled": False,
                "payouts_enabled": False,
                "error": "Impossibile verificare lo stato"
            }


@router.get("/api/stripe/connect/dashboard")
async def connect_dashboard(request: Request):
    """Genera un link alla Express Dashboard di Stripe per il consulente"""
    user = verify_token(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    stripe = _get_stripe()
    
    with Session(engine) as session:
        db_user = session.get(User, user.id)
        if not db_user or not db_user.stripe_account_id:
            raise HTTPException(status_code=400, detail="Account Stripe non collegato")
        
        try:
            login_link = stripe.Account.create_login_link(db_user.stripe_account_id)
            return {"success": True, "url": login_link.url}
        except Exception as e:
            logger.error(f"Errore creazione dashboard link: {e}")
            raise HTTPException(status_code=500, detail="Errore nella generazione del link alla dashboard")
