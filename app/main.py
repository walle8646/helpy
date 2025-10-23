from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routes import home, api, user_register, user_login, user_profile, public_profile, consultants
from app.database import create_db_and_tables
from app.logger_config import logger
from pathlib import Path

app = FastAPI()

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 🔥 Monta la cartella uploads
uploads_dir = Path("app/static/uploads")
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory="app/static/uploads"), name="uploads")

# Routes - ORDINE IMPORTANTE!
app.include_router(home.router)
app.include_router(api.router)
app.include_router(user_register.router)
app.include_router(user_login.router)       # Login/Logout
app.include_router(user_profile.router)     # 🔥 /profile con categorie
app.include_router(public_profile.router)
app.include_router(consultants.router)

@app.on_event("startup")
def on_startup():
    logger.info("Avvio applicazione FastAPI")
    create_db_and_tables()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from app.models_user import User
from app.database import get_session
from app.auth import verify_token, create_token
from app.logger_config import logger
import hashlib

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/api/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    password_md5 = hashlib.md5(password.encode()).hexdigest()
    
    # 🔥 USA WITH per il context manager
    with get_session() as session:
        user = session.exec(select(User).where(User.email == email)).first()
        
        if not user:
            return JSONResponse({"error": "Email not found"}, status_code=404)
        
        if user.password_md5 != password_md5:
            return JSONResponse({"error": "Wrong password"}, status_code=401)
        
        if user.confirmed != 1:
            return JSONResponse({"error": "Please confirm your email first"}, status_code=403)
        
        token = create_token({"user_id": user.id})
        
        response = JSONResponse({"message": "Login successful", "redirect": "/profile"})
        response.set_cookie(key="session_token", value=token, httponly=True, max_age=86400*7)
        
        logger.info(f"User logged in: {user.email}")
        return response

@router.get("/logout")
def logout():
    response = RedirectResponse("/")
    response.delete_cookie("session_token")
    return response
