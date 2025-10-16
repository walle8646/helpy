import hashlib
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
    msg.set_content(f"Ciao,\n\ngrazie per esserti registrato su MyApp.\nIl tuo codice di conferma è: {code}\nInseriscilo nella pagina di conferma per completare la registrazione.\n\nSe non hai richiesto questa registrazione, ignora questa email.\n\nGrazie,\nMyApp Team")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASSWORD)
        s.send_message(msg)
