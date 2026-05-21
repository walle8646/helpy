"""
Helper per inviare email scegliendo backend in base a env.

Priorità (la prima che matcha vince):
1. EMAIL_BACKEND=smtp  → smtplib (per dev locale con Mailpit o SMTP custom)
2. RESEND_API_KEY      → Resend HTTP API (provider primario)
3. SendGrid            → fallback legacy se solo SENDGRID_API_KEY è settata

L'API è progettata come drop-in per le chiamate esistenti:
    sg = SendGridAPIClient(api_key); response = sg.send(message)
diventa:
    response = mail_send(api_key, message)

Il parametro `api_key` è quello legacy (SendGrid). Per Resend si legge `RESEND_API_KEY` da env.
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from types import SimpleNamespace

from app.logger_config import logger

try:
    from sendgrid import SendGridAPIClient  # noqa: F401  (re-exported)
except Exception:  # pragma: no cover
    SendGridAPIClient = None  # type: ignore

try:
    import resend  # type: ignore
except Exception:  # pragma: no cover
    resend = None  # type: ignore


def _use_smtp_backend() -> bool:
    return os.getenv("EMAIL_BACKEND", "").lower() == "smtp"


def is_backend_available() -> bool:
    """True se è configurato almeno un backend email valido (SMTP, Resend o SendGrid)."""
    if _use_smtp_backend():
        return True
    if _resend_api_key():
        return True
    # SendGrid legacy: serve sia il package sia una key non-placeholder
    sg_key = os.getenv("SENDGRID_API_KEY") or os.getenv("SMTP_PASSWORD") or ""
    sg_key = sg_key.strip()
    if SendGridAPIClient is not None and sg_key and not sg_key.startswith(("dev-", "placeholder")):
        return True
    return False


def active_backend_name() -> str:
    """Nome del backend che verrebbe usato adesso (utile per log)."""
    if _use_smtp_backend():
        return "SMTP"
    if _resend_api_key():
        return "Resend"
    return "SendGrid"


def _resend_api_key() -> str:
    """Ritorna la API key Resend solo se è una chiave reale (non placeholder)."""
    k = os.getenv("RESEND_API_KEY", "").strip()
    if not k or k.startswith(("dev-", "placeholder", "test-dummy")):
        return ""
    return k


def _smtp_use_tls() -> bool:
    return os.getenv("SMTP_USE_TLS", "true").lower() not in ("false", "0", "no")


def _extract_sg_message(message):
    """Estrae from/to/subject/html da un sendgrid.helpers.mail.Mail."""
    data = message.get() if hasattr(message, "get") else dict(message)
    from_data = data.get("from") or {}
    from_email = from_data.get("email")
    from_name = from_data.get("name")
    subject = data.get("subject")
    personalizations = data.get("personalizations") or [{}]
    tos = [t.get("email") for t in (personalizations[0].get("to") or []) if t.get("email")]
    html = None
    for c in data.get("content") or []:
        if c.get("type") == "text/html":
            html = c.get("value")
            break
    return from_email, from_name, tos, subject, html


def _format_from(from_email: str, from_name: str | None) -> str:
    if from_name:
        return f"{from_name} <{from_email}>"
    return from_email


def _send_via_smtp(from_email, from_name, tos, subject, html):
    host = os.getenv("SMTP_HOST", "localhost")
    port = int(os.getenv("SMTP_PORT", "1025"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject or "(no subject)"
    msg["From"] = _format_from(from_email, from_name) if from_email else os.getenv("EMAIL_FROM", "noreply@ispiramy.com")
    msg["To"] = ", ".join(tos)
    msg.attach(MIMEText(html or "", "html"))

    with smtplib.SMTP(host, port, timeout=15) as server:
        if _smtp_use_tls():
            server.starttls()
            if user and password:
                server.login(user, password)
        server.send_message(msg)

    logger.info(f"📨 [SMTP] Email inviata a {tos} via {host}:{port}")
    return SimpleNamespace(status_code=202, body=b"", headers={})


def _send_via_resend(from_email, from_name, tos, subject, html):
    if resend is None:
        raise RuntimeError("resend package non installato (pip install resend)")
    api_key = _resend_api_key()
    if not api_key:
        raise RuntimeError("RESEND_API_KEY non configurata")
    resend.api_key = api_key

    sender = _format_from(from_email, from_name) if from_email else os.getenv("EMAIL_FROM", "noreply@ispiramy.com")
    params = {
        "from": sender,
        "to": tos,
        "subject": subject or "(no subject)",
        "html": html or "",
    }
    try:
        result = resend.Emails.send(params)
        msg_id = result.get("id") if isinstance(result, dict) else None
        logger.info(f"📨 [Resend] Email inviata a {tos} (id={msg_id})")
        return SimpleNamespace(status_code=202, body=str(result).encode(), headers={"Message-Id": msg_id or ""})
    except Exception as e:
        logger.error(f"❌ [Resend] Errore invio a {tos}: {e}")
        return SimpleNamespace(status_code=500, body=str(e).encode(), headers={})


def mail_send(api_key, message):
    """Invia un sendgrid.helpers.mail.Mail tramite il backend configurato."""
    from_email, from_name, tos, subject, html = _extract_sg_message(message)

    if _use_smtp_backend():
        if not tos:
            logger.warning("⚠️ [SMTP] Nessun destinatario nel Mail message.")
            return SimpleNamespace(status_code=400, body=b"no recipients", headers={})
        return _send_via_smtp(from_email, from_name, tos, subject, html)

    # Resend ha priorità sul legacy SendGrid se la chiave è settata
    if _resend_api_key():
        if not tos:
            logger.warning("⚠️ [Resend] Nessun destinatario nel Mail message.")
            return SimpleNamespace(status_code=400, body=b"no recipients", headers={})
        return _send_via_resend(from_email, from_name, tos, subject, html)

    # Fallback legacy SendGrid
    if SendGridAPIClient is None:
        raise RuntimeError("Nessun backend email disponibile (RESEND_API_KEY mancante e sendgrid non installato)")
    return SendGridAPIClient(api_key).send(message)
