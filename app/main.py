import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.database import create_db_and_tables
from app.routes import home, auth, consultants, user_profile

app = FastAPI(title="Helpy", version="1.0.0")

# Templates
templates = Jinja2Templates(directory="app/templates")
app.state.templates = templates

# Crea directory uploads se non esiste
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
(UPLOAD_DIR / "profile_pictures").mkdir(exist_ok=True)

# Monta static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include routes
app.include_router(home.router)
app.include_router(auth.router)
app.include_router(user_profile.router)  # ✅ Già include /user/{user_id}
app.include_router(consultants.router)

# Crea tabelle al startup
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/")
async def root():
    return {"message": "Helpy API is running"}

# === ESECUZIONE LOCALE ===
if __name__ == "__main__":
    import uvicorn
    # Leggi porta da variabile d'ambiente (default 8080 in locale)
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
