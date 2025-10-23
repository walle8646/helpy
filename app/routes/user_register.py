from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from app.models import User
from app.database import get_session
from app.utils_user import hash_md5, gen_code6, send_confirmation_email
from app.logger_config import logger
import re

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w+$"

@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/api/register")
def register_user(email: str = Form(...), password: str = Form(...)):
    email = email.strip().lower()
    if not re.match(EMAIL_REGEX, email):
        return JSONResponse({"error": "Invalid email format"}, status_code=400)
    if len(password) < 8:
        return JSONResponse({"error": "Password too short"}, status_code=400)
    with get_session() as session:
        if session.exec(select(User).where(User.email == email)).first():
            return JSONResponse({"error": "Email already registered"}, status_code=409)
        pwd_md5 = hash_md5(password)
        code = gen_code6()
        user = User(email=email, password_md5=pwd_md5, confirmation_code=code, confirmed=0)
        session.add(user)
        session.commit()
        logger.info(f"User registered: {email}")
        try:
            send_confirmation_email(email, code)
            logger.info(f"Confirmation email sent to: {email}")
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return JSONResponse({"error": "Failed to send confirmation email"}, status_code=500)
    return JSONResponse({"message": "User registered, confirmation code sent"}, status_code=201)

@router.post("/api/confirm")
def confirm_user(email: str = Form(...), code: str = Form(...)):
    email = email.strip().lower()
    with get_session() as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if not user or user.confirmation_code != code:
            return JSONResponse({"error": "Invalid code or email"}, status_code=400)
        user.confirmed = 1
        user.confirmation_code = None
        session.add(user)
        session.commit()
        logger.info(f"User confirmed: {email}")
    return JSONResponse({"message": "User confirmed"}, status_code=200)
