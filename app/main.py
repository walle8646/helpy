import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.database import create_db_and_tables
from app.routes import home, auth, consultants, user_profile, messages, community, public_profile, availability, booking, consultation, stripe_webhook, notifications
from app.logger_config import logger
from app.scheduler import start_scheduler, shutdown_scheduler
from app.utils.template_helpers import get_all_categories
from app.utils_user import get_display_name

app = FastAPI(title="Helpy", version="1.0.0")


# Middleware per aggiungere categorie globalmente ai template
class CategoriesMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Carica categorie e le rende disponibili nel request.state
        request.state.categories = get_all_categories()
        response = await call_next(request)
        return response


# Session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "helpy-super-secret-key-change-in-production-2024"),
    max_age=86400
)

# Aggiungi middleware categorie
app.add_middleware(CategoriesMiddleware)

# Templates
templates = Jinja2Templates(directory="app/templates")
# Aggiungi filtro personalizzato per nomi utenti
templates.env.filters['display_name'] = get_display_name
app.state.templates = templates

# Crea directory uploads
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
(UPLOAD_DIR / "profile_pictures").mkdir(exist_ok=True)

# Monta static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include routes
app.include_router(home.router, tags=["home"])
app.include_router(auth.router, tags=["auth"])
app.include_router(user_profile.router, tags=["profile"])
app.include_router(public_profile.router, tags=["public_profile"])
app.include_router(consultants.router, tags=["consultants"])
app.include_router(messages.router, tags=["messages"])  # ✅ Aggiungi questo
app.include_router(community.router)
app.include_router(availability.router, tags=["availability"])
app.include_router(booking.router, tags=["booking"])
app.include_router(consultation.router, tags=["consultation"])
app.include_router(stripe_webhook.router, tags=["webhooks"])
app.include_router(notifications.router, tags=["notifications"])


# Database init
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    start_scheduler()  # Avvia lo scheduler per le notifiche programmate
    logger.info("✅ Helpy started successfully")


@app.on_event("shutdown")
def on_shutdown():
    shutdown_scheduler()  # Ferma lo scheduler in modo pulito
    logger.info("👋 Helpy shutting down")


# Esecuzione locale
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)
