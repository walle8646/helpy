import os

# Imposta il percorso base alla cartella 'app' esterna rispetto a 'setup_file'
base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app'))

files = {
    "models_user.py": '''from sqlmodel import SQLModel, Field
from typing import Optional

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, nullable=False, unique=True)
    password_md5: str = Field(nullable=False)
    confirmation_code: Optional[str] = Field(default=None, max_length=6)
    confirmed: int = Field(default=0)
    created_at: Optional[str] = Field(default=None)
''',

    "utils_user.py": '''import hashlib
import random
import smtplib
from email.message import EmailMessage
import os

def hash_md5(password: str) -> str:
    return hashlib.md5(password.encode('utf-8')).hexdigest()

def gen_code6() -> str:
    return f"{random.randint(0, 999999):06d}"

def send_confirmation_email(to_email: str, code: str):
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    EMAIL_FROM = os.getenv("EMAIL_FROM", "MyApp <no-reply@example.com>")

    msg = EmailMessage()
    msg['Subject'] = 'Conferma la tua registrazione su MyApp'
    msg['From'] = EMAIL_FROM
    msg['To'] = to_email
    msg.set_content(f"Ciao,\\n\\ngrazie per esserti registrato su MyApp.\\nIl tuo codice di conferma è: {code}\\nInseriscilo nella pagina di conferma per completare la registrazione.\\n\\nSe non hai richiesto questa registrazione, ignora questa email.\\n\\nGrazie,\\nMyApp Team")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASSWORD)
        s.send_message(msg)
''',

    "routes/user_register.py": '''from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from app.models_user import User
from app.database import get_session
from app.utils_user import hash_md5, gen_code6, send_confirmation_email
from app.logger_config import logger
import re

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

EMAIL_REGEX = r"^[\\w\\.-]+@[\\w\\.-]+\\.\\w+$"

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
''',

    "templates/register.html": '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Register - Helpy</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <h2>Register</h2>
    <form method="post" action="/api/register">
        <label>Email:<br><input type="email" name="email" required></label><br><br>
        <label>Password:<br><input type="password" name="password" minlength="8" required></label><br><br>
        <button type="submit">Register</button>
    </form>
</body>
</html>
'''
}

for path, content in files.items():
    full_path = os.path.join(base, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("File per la registrazione utente creati!")