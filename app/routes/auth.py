import jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.database import get_session
from app.models import User
from passlib.context import CryptContext

SECRET_KEY = "your-secret-key-change-this-in-production-123456789"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crea un JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    """Verifica e decodifica un JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception("Token expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid token")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Pagina di login"""
    return templates.TemplateResponse("auth/login.html", {"request": request})

@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session)
):
    """Gestisce il login"""
    # Trova utente
    statement = select(User).where(User.email == email)
    user = session.exec(statement).first()
    
    if not user or not pwd_context.verify(password, user.password):
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Email o password errati"}
        )
    
    # Salva user_id in session (usa cookie sicuro in produzione)
    response = RedirectResponse(url="/profile", status_code=303)
    response.set_cookie(key="user_id", value=str(user.id))
    return response

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Pagina di registrazione"""
    return templates.TemplateResponse("auth/register.html", {"request": request})

@router.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    nome: str = Form(...),
    session: Session = Depends(get_session)
):
    """Gestisce la registrazione"""
    # Verifica se email già esiste
    statement = select(User).where(User.email == email)
    existing_user = session.exec(statement).first()
    
    if existing_user:
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "error": "Email già registrata"}
        )
    
    # Crea nuovo utente
    hashed_password = pwd_context.hash(password)
    new_user = User(
        email=email,
        password=hashed_password,
        nome=nome,
        confirmed=True
    )
    
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    # Redirect a login
    return RedirectResponse(url="/login", status_code=303)

@router.get("/logout")
async def logout():
    """Logout"""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="user_id")
    return response