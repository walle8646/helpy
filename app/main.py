import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from app.database import create_db_and_tables
from app.routes import home, auth, consultants, user_profile, messages, community, public_profile, availability, booking
from app.logger_config import logger

app = FastAPI(title="Helpy", version="1.0.0")

# Session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "helpy-super-secret-key-change-in-production-2024"),
    max_age=86400
)

# Templates
templates = Jinja2Templates(directory="app/templates")
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


# Database init
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    logger.info("✅ Helpy started successfully")

# Esecuzione locale
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)
