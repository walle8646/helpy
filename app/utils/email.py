import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from app.logger_config import logger
import secrets
import string

def generate_verification_code() -> str:
    """Genera codice di verifica a 6 cifre.

    Usa `secrets` e non `random`: questi codici valgono come credenziale per
    confermare l'email e per il reset password, quindi non devono essere
    prevedibili a partire da altri codici osservati.
    """
    return ''.join(secrets.choice(string.digits) for _ in range(6))

def send_verification_email(to_email: str, code: str, nome: str = "User") -> bool:
    """Invia email di verifica tramite SendGrid API HTTP"""
    
    from app.utils.email_backend import is_backend_available, active_backend_name
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY") or os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("FROM_EMAIL") or os.getenv("EMAIL_FROM")

    if not from_email:
        logger.error("❌ FROM_EMAIL not configured")
        return False
    if not is_backend_available():
        logger.error("❌ Nessun backend email disponibile (configura RESEND_API_KEY o SENDGRID_API_KEY o EMAIL_BACKEND=smtp)")
        return False
    
    try:
        from app.utils.notification_email import _branded_email
        _code_box = (
            '<div style="font-size:34px;font-weight:800;letter-spacing:8px;color:#2e7d32;'
            'background:#e8f5e9;border-radius:10px;padding:22px;text-align:center;margin:24px 0;">'
            f'{code}</div>'
        )
        _body = (
            f"<p>Ciao <strong>{nome}</strong>! 👋</p>"
            "<p>Grazie per esserti registrato su Ispiramy! Per completare la registrazione, inserisci questo codice di verifica:</p>"
            + _code_box +
            "<p>Il codice è valido <strong>15 minuti</strong>. Se non hai richiesto questa registrazione, ignora questa email.</p>"
        )
        html_body = _branded_email("✨", "Conferma la tua email", "#43a047", "#2e7d32", _body)

        message = Mail(
            from_email=Email(from_email),
            to_emails=To(to_email),
            subject='Conferma la tua email - Ispiramy',
            html_content=Content("text/html", html_body)
        )
        
        from app.utils.email_backend import mail_send
        response = mail_send(sendgrid_api_key, message)
        
        logger.info(f"✅ Verification email sent to {to_email} via {active_backend_name()} (status: {response.status_code})")
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to send verification email to {to_email}: {e}", exc_info=True)
        return False

def send_profile_verification_request(to_email: str, user_id: int, user_name: str, user_email: str) -> bool:
    """Invia email ai verifiers quando un utente modifica il profilo e soddisfa i requisiti"""
    
    from app.utils.email_backend import is_backend_available, active_backend_name
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY") or os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("FROM_EMAIL") or os.getenv("EMAIL_FROM")

    if not from_email:
        logger.error("❌ FROM_EMAIL not configured")
        return False
    if not is_backend_available():
        logger.error("❌ Nessun backend email disponibile (configura RESEND_API_KEY o SENDGRID_API_KEY o EMAIL_BACKEND=smtp)")
        return False
    
    try:
        from app.utils.notification_email import _branded_email
        _base = os.getenv("BASE_URL", "")
        _body = (
            f"<p>L'utente <strong>{user_name}</strong> ha aggiornato il profilo e ha completato tutti i requisiti per la verifica:</p>"
            '<ul style="line-height:1.8;color:#374151;">'
            "<li>✅ Professione specificata</li>"
            "<li>✅ Categoria selezionata</li>"
            "<li>✅ Aree di interesse definite</li>"
            "<li>✅ Descrizione completa (minimo 200 caratteri)</li>"
            "</ul>"
            '<div style="background:#f9fafb;border-left:4px solid #43a047;border-radius:6px;padding:14px 18px;margin:20px 0;">'
            f"<p style='margin:0;'><strong>Email utente:</strong> {user_email}</p>"
            f"<p style='margin:8px 0 0;'><strong>ID utente:</strong> {user_id}</p></div>"
            "<p>Accedi al pannello per verificare il profilo e assegnare il badge verificato.</p>"
        )
        html_body = _branded_email("🔍", "Nuovo profilo da verificare", "#43a047", "#2e7d32", _body, "Visualizza Profilo", f"{_base}/user/{user_id}")

        message = Mail(
            from_email=Email(from_email),
            to_emails=To(to_email),
            subject=f'Richiesta Verifica Profilo - {user_name}',
            html_content=Content("text/html", html_body)
        )
        
        from app.utils.email_backend import mail_send
        response = mail_send(sendgrid_api_key, message)
        
        logger.info(f"✅ Profile verification request sent to {to_email} for user {user_name} (ID: {user_id}) via {active_backend_name()} (status: {response.status_code})")
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to send profile verification request to {to_email}: {e}", exc_info=True)
        return False


def send_email(recipient_email: str, subject: str, html_content: str) -> bool:
    """Invia email generica tramite SendGrid API"""
    
    from app.utils.email_backend import is_backend_available, active_backend_name
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY") or os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("FROM_EMAIL") or os.getenv("EMAIL_FROM")

    if not from_email:
        logger.error("❌ FROM_EMAIL not configured")
        return False
    if not is_backend_available():
        logger.error("❌ Nessun backend email disponibile (configura RESEND_API_KEY o SENDGRID_API_KEY o EMAIL_BACKEND=smtp)")
        return False
    
    try:
        message = Mail(
            from_email=Email(from_email),
            to_emails=To(recipient_email),
            subject=subject,
            html_content=Content("text/html", html_content)
        )
        
        from app.utils.email_backend import mail_send
        response = mail_send(sendgrid_api_key, message)
        
        logger.info(f"✅ Email sent to {recipient_email} (subject: {subject}) via {active_backend_name()} (status: {response.status_code})")
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to send email to {recipient_email}: {e}", exc_info=True)
        return False