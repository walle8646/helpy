from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.database import get_session
from app.models import User
from sqlmodel import select
import hashlib
from typing import Optional

router = APIRouter()

def verify_token(request: Request) -> Optional[User]:
    """Verifica se l'utente è loggato tramite session"""
    user_id = request.session.get("user_id")
    
    if not user_id:
        return None
    
    with get_session() as session:
        user = session.get(User, user_id)
        return user

async def get_current_user(request: Request) -> User:
    """Dependency che richiede autenticazione"""
    user = verify_token(request)
    if not user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    return user

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Pagina di login"""
    # ❌ RIMUOVI QUESTO (causa loop):
    # if verify_token(request):
    #     return RedirectResponse("/profile", status_code=302)
    
    # ✅ Mostra sempre la pagina login
    return request.app.state.templates.TemplateResponse(
        "login.html",
        {"request": request}
    )

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
        
        # ✅ SALVA IN SESSION
        request.session["user_id"] = user.id
        request.session["user_email"] = user.email
        request.session["user_nome"] = user.nome or "User"
        
        # ✅ REDIRECT A /profile
        return RedirectResponse("/profile", status_code=302)

@router.post("/api/login")
async def api_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    """API Login (ritorna JSON)"""
    with get_session() as session:
        statement = select(User).where(User.email == email)
        user = session.exec(statement).first()
        
        if not user:
            return JSONResponse({"error": "Email non trovata"}, status_code=404)
        
        password_hash = hashlib.md5(password.encode()).hexdigest()
        
        if user.password_md5 != password_hash:
            return JSONResponse({"error": "Password errata"}, status_code=401)
        
        if user.confirmed != 1:
            return JSONResponse({"error": "Conferma la tua email"}, status_code=403)
        
        # ✅ SALVA IN SESSION
        request.session["user_id"] = user.id
        request.session["user_email"] = user.email
        
        return JSONResponse({
            "message": "Login successful",
            "redirect_url": "/profile",  # ✅ /profile
            "user": {
                "id": user.id,
                "email": user.email,
                "nome": user.nome
            }
        })

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Pagina di registrazione"""
    return request.app.state.templates.TemplateResponse(
        "register.html",
        {"request": request}
    )

@router.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    nome: str = Form(...),
    cognome: str = Form(None)
):
    """Gestisce la registrazione"""
    with get_session() as session:
        existing = session.exec(select(User).where(User.email == email)).first()
        if existing:
            return request.app.state.templates.TemplateResponse(
                "register.html",
                {"request": request, "error": "Email già registrata"}
            )
        
        password_hash = hashlib.md5(password.encode()).hexdigest()
        
        new_user = User(
            email=email,
            password_md5=password_hash,
            nome=nome,
            cognome=cognome,
            confirmed=0
        )
        
        session.add(new_user)
        session.commit()
        
        return RedirectResponse("/login?registered=true", status_code=302)

@router.get("/logout")
async def logout(request: Request):
    """Logout utente"""
    request.session.clear()
    return RedirectResponse("/", status_code=302)