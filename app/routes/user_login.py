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
