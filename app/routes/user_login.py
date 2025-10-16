from fastapi import APIRouter, Request, Form, Response, Header
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from app.models_user import User
from app.database import get_session
from app.utils_user import hash_md5, gen_code6, send_password_reset_email
from app.auth import create_access_token
from app.logger_config import logger
import re

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w+$"

@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/api/login")
def login_user(email: str = Form(...), password: str = Form(...)):
    email = email.strip().lower()
    if not re.match(EMAIL_REGEX, email):
        return JSONResponse({"error": "Invalid email format"}, status_code=400)
    
    with get_session() as session:
        user = session.exec(select(User).where(User.email == email)).first()
        
        if not user:
            return JSONResponse({"error": "email_not_found"}, status_code=404)
        
        pwd_md5 = hash_md5(password)
        if user.password_md5 != pwd_md5:
            return JSONResponse({"error": "wrong_password"}, status_code=401)
        
        if user.confirmed != 1:
            return JSONResponse({"error": "account_not_confirmed"}, status_code=403)
        
        # Crea il token JWT
        access_token = create_access_token(data={"user_id": user.id, "email": user.email})
        
        logger.info(f"User logged in: {email}, creating cookie with token")
        
        # Crea la risposta JSON
        response = JSONResponse({
            "message": "Login successful",
            "redirect": "/profile"
        }, status_code=200)
        
        # Imposta il cookie con path esplicito
        response.set_cookie(
            key="session_token",
            value=access_token,
            httponly=True,
            max_age=60 * 60 * 24 * 7,  # 7 giorni
            path="/",  # IMPORTANTE: aggiungi path
            samesite="lax",
            secure=False  # False per localhost HTTP
        )
        
        logger.info(f"Cookie set for user: {email}")
        return response

@router.get("/profile", response_class=HTMLResponse)
def user_profile(request: Request, authorization: str = Header(None)):
    # Prova prima dall'header Authorization
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
    
    # Se non c'è nell'header, prova dal cookie
    if not token:
        token = request.cookies.get("session_token")
    
    logger.info(f"Profile accessed, token: {token[:20] if token else 'None'}...")
    
    if not token:
        logger.warning("No session token found, redirecting to login")
        return RedirectResponse("/login")
    
    try:
        from app.auth import verify_token
        payload = verify_token(token)
        user_id = payload.get("user_id")
        logger.info(f"Token verified, user_id: {user_id}")
        
        if not user_id:
            logger.warning("No user_id in token")
            return RedirectResponse("/login")
        
        with get_session() as session:
            user = session.get(User, user_id)
            if not user:
                logger.warning(f"User {user_id} not found in database")
                return RedirectResponse("/login")
            
            logger.info(f"User {user.email} loaded successfully")
            return templates.TemplateResponse("profile.html", {
                "request": request,
                "user": user
            })
    except Exception as e:
        logger.error(f"Error in profile: {e}")
        return RedirectResponse("/login")

@router.get("/logout")
def logout(response: Response):
    response = RedirectResponse("/login")
    response.delete_cookie("session_token")
    return response

@router.post("/api/request-password-reset")
def request_password_reset(email: str = Form(...)):
    email = email.strip().lower()
    with get_session() as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            return JSONResponse({"error": "Email not found"}, status_code=404)
        
        reset_code = gen_code6()
        user.confirmation_code = reset_code
        session.add(user)
        session.commit()
        
        try:
            send_password_reset_email(email, reset_code)
            logger.info(f"Password reset email sent to: {email}")
            return JSONResponse({"message": "Reset code sent to your email"}, status_code=200)
        except Exception as e:
            logger.error(f"Error sending reset email: {e}")
            return JSONResponse({"error": "Failed to send email"}, status_code=500)

@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_form(request: Request, code: str = None):
    return templates.TemplateResponse("reset_password.html", {
        "request": request,
        "code": code
    })

@router.post("/api/reset-password")
def reset_password(email: str = Form(...), code: str = Form(...), new_password: str = Form(...)):
    email = email.strip().lower()
    if len(new_password) < 8:
        return JSONResponse({"error": "Password must be at least 8 characters"}, status_code=400)
    
    with get_session() as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if not user or user.confirmation_code != code:
            return JSONResponse({"error": "Invalid code or email"}, status_code=400)
        
        user.password_md5 = hash_md5(new_password)
        user.confirmation_code = None
        session.add(user)
        session.commit()
        logger.info(f"Password reset for: {email}")
        return JSONResponse({"message": "Password updated successfully"}, status_code=200)
