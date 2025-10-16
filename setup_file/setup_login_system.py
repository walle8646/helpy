import os

# Imposta il percorso base alla cartella 'app' esterna rispetto a 'setup_file'
base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app'))

files = {
    "routes/user_login.py": '''from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from app.models_user import User
from app.database import get_session
from app.utils_user import hash_md5, gen_code6, send_password_reset_email
from app.logger_config import logger
import re

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

EMAIL_REGEX = r"^[\\w\\.-]+@[\\w\\.-]+\\.\\w+$"

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
        
        logger.info(f"User logged in: {email}")
        return JSONResponse({"message": "Login successful", "redirect": f"/profile/{user.id}"}, status_code=200)

@router.get("/profile/{user_id}", response_class=HTMLResponse)
def user_profile(request: Request, user_id: int):
    with get_session() as session:
        user = session.get(User, user_id)
        if not user:
            return RedirectResponse("/login")
        return templates.TemplateResponse("profile.html", {
            "request": request,
            "user": user
        })

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
''',

    "templates/login.html": '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Helpy</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <nav class="navbar">
        <div class="navbar-left">
            <img src="https://i.imgur.com/4M34hi2.png" alt="Helpy Logo" class="navbar-logo" style="height:32px;">
            <span class="navbar-title">Helpy</span>
        </div>
        <div class="navbar-links">
            <a href="/">Home</a>
        </div>
    </nav>

    <div class="register-container">
        <div class="register-header">
            <h1>Welcome Back</h1>
            <p>Log in to your Helpy account</p>
        </div>
        
        <div id="errorMessage" class="error-message"></div>
        <div id="emailNotFound" class="error-message" style="display:none;">
            <p>Email not found. <a href="/register" style="color:#2563eb; font-weight:600;">Create a new account</a></p>
        </div>
        <div id="wrongPassword" class="error-message" style="display:none;">
            <p>Wrong password. <a href="#" id="resetPasswordLink" style="color:#2563eb; font-weight:600;">Reset your password</a></p>
        </div>

        <form class="register-form" id="loginForm">
            <div class="form-group">
                <label for="email">Email Address</label>
                <input type="email" id="email" name="email" required placeholder="your@email.com">
            </div>
            
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required placeholder="Enter your password">
            </div>
            
            <button type="submit" class="register-form-btn">Log In</button>
        </form>

        <div class="back-link">
            <a href="/">← Back to Home</a>
        </div>
    </div>

    <script src="/static/script.js"></script>
</body>
</html>
''',

    "templates/profile.html": '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Profile - Helpy</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <nav class="navbar">
        <div class="navbar-left">
            <img src="https://i.imgur.com/4M34hi2.png" alt="Helpy Logo" class="navbar-logo" style="height:32px;">
            <span class="navbar-title">Helpy</span>
        </div>
        <div class="navbar-links">
            <a href="/">Home</a>
            <a href="/login">Logout</a>
        </div>
    </nav>

    <div class="register-container">
        <div class="register-header">
            <h1>👤 Your Profile</h1>
            <p>Welcome to your Helpy account</p>
        </div>

        <div class="profile-info">
            <div class="profile-field">
                <label>Email:</label>
                <p>{{ user.email }}</p>
            </div>
            <div class="profile-field">
                <label>Password:</label>
                <p>{{ user.password_md5[:8] }}••••••••</p>
            </div>
            <div class="profile-field">
                <label>Account Status:</label>
                <p>{% if user.confirmed == 1 %}<span style="color:#4a4;">✓ Verified</span>{% else %}<span style="color:#c33;">Not Verified</span>{% endif %}</p>
            </div>
        </div>

        <div class="back-link">
            <a href="/">← Back to Home</a>
        </div>
    </div>
</body>
</html>
''',

    "templates/reset_password.html": '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Password - Helpy</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <nav class="navbar">
        <div class="navbar-left">
            <img src="https://i.imgur.com/4M34hi2.png" alt="Helpy Logo" class="navbar-logo" style="height:32px;">
            <span class="navbar-title">Helpy</span>
        </div>
        <div class="navbar-links">
            <a href="/">Home</a>
        </div>
    </nav>

    <div class="register-container">
        <!-- Step 1: Request Reset -->
        <div id="requestStep" class="register-step">
            <div class="register-header">
                <h1>Reset Your Password</h1>
                <p>Enter your email to receive a reset code</p>
            </div>
            
            <div id="errorMessage" class="error-message"></div>

            <form class="register-form" id="requestResetForm">
                <div class="form-group">
                    <label for="email">Email Address</label>
                    <input type="email" id="email" name="email" required placeholder="your@email.com">
                </div>
                
                <button type="submit" class="register-form-btn">Send Reset Code</button>
            </form>
        </div>

        <!-- Step 2: Enter Code and New Password -->
        <div id="resetStep" class="register-step" style="display:none;">
            <div class="register-header">
                <h1>Enter Reset Code</h1>
                <p>Check your email for the 6-digit code</p>
            </div>
            
            <div id="resetErrorMessage" class="error-message"></div>
            <div id="successMessage" class="success-message"></div>

            <form class="register-form" id="resetPasswordForm">
                <div class="form-group">
                    <label for="code">Reset Code</label>
                    <input type="text" id="code" name="code" required placeholder="123456" maxlength="6" pattern="\\d{6}">
                </div>
                <div class="form-group">
                    <label for="newPassword">New Password</label>
                    <input type="password" id="newPassword" name="new_password" minlength="8" required placeholder="At least 8 characters">
                </div>
                
                <button type="submit" class="register-form-btn">Reset Password</button>
            </form>
        </div>

        <div class="back-link">
            <a href="/login">← Back to Login</a>
        </div>
    </div>

    <script src="/static/script.js"></script>
</body>
</html>
''',
}

for path, content in files.items():
    full_path = os.path.join(base, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("File per il sistema di login creati!")