"""
Agora RTC Token Generator e Access Token per Cloud Recording
Genera token sicuri per le video call e cloud recording con Agora.io
"""
import os
import time
import hmac
import hashlib
import base64
from agora_token_builder import RtcTokenBuilder
from dotenv import load_dotenv

load_dotenv()

# Credenziali Agora
AGORA_APP_ID = os.getenv("AGORA_APP_ID")
AGORA_APP_CERTIFICATE = os.getenv("AGORA_APP_CERTIFICATE")

# Role definitions
ROLE_PUBLISHER = 1  # Can publish and subscribe
ROLE_SUBSCRIBER = 2  # Can only subscribe

def generate_agora_token(
    channel_name: str,
    uid: int = 0,
    role: int = ROLE_PUBLISHER,
    expiration_seconds: int = 3600
) -> dict:
    """
    Genera un token RTC Agora per un utente specifico.
    
    Args:
        channel_name: Nome del canale (es: "booking_123")
        uid: User ID (0 = any user, >0 = specific user)
        role: ROLE_PUBLISHER (1) o ROLE_SUBSCRIBER (2)
        expiration_seconds: Durata token in secondi (default 1 ora)
    
    Returns:
        dict con token, app_id, channel_name, uid, expiration
    """
    if not AGORA_APP_ID or not AGORA_APP_CERTIFICATE:
        raise ValueError("AGORA_APP_ID and AGORA_APP_CERTIFICATE must be set in .env")
    
    # Calcola timestamp di scadenza
    current_timestamp = int(time.time())
    privilege_expired_ts = current_timestamp + expiration_seconds
    
    # Genera il token
    token = RtcTokenBuilder.buildTokenWithUid(
        AGORA_APP_ID,
        AGORA_APP_CERTIFICATE,
        channel_name,
        uid,
        role,
        privilege_expired_ts
    )
    
    return {
        "token": token,
        "app_id": AGORA_APP_ID,
        "channel_name": channel_name,
        "uid": uid,
        "expiration": privilege_expired_ts
    }


def generate_booking_call_token(booking_id: int, user_id: int) -> dict:
    """
    Genera un token per una specifica prenotazione.
    Il channel_name è basato sul booking_id per garantire che client e consultant
    entrino nello stesso canale.
    
    Args:
        booking_id: ID della prenotazione
        user_id: ID dell'utente (client o consultant)
    
    Returns:
        dict con token e credenziali
    """
    channel_name = f"booking_{booking_id}"
    
    # Durata token: 2 ore (per consulenze lunghe + buffer)
    expiration_seconds = 7200
    
    return generate_agora_token(
        channel_name=channel_name,
        uid=user_id,
        role=ROLE_PUBLISHER,  # Entrambi possono pubblicare video/audio
        expiration_seconds=expiration_seconds
    )


def generate_access_token(expiration_seconds: int = 3600) -> str:
    """
    Genera un Access Token per Agora Cloud Recording API.
    
    L'Access Token è diverso dal RTC Token ed è utilizzato per:
    - Cloud Recording API (acquire, start, stop)
    - Non è necessario specificare channel o uid
    - Valida solo le credenziali API (App ID)
    
    Args:
        expiration_seconds: Durata token in secondi (default 1 ora)
    
    Returns:
        str con l'Access Token
    
    Reference:
    https://docs.agora.io/en/cloud-recording/reference/cloud-recording-api?platform=RESTful#authorization
    """
    if not AGORA_APP_ID or not AGORA_APP_CERTIFICATE:
        raise ValueError("AGORA_APP_ID and AGORA_APP_CERTIFICATE must be set in .env")
    
    # Calcola timestamp di scadenza
    current_timestamp = int(time.time())
    expire_timestamp = current_timestamp + expiration_seconds
    
    # Format: appId + expire_timestamp
    message_to_sign = f"{AGORA_APP_ID}{expire_timestamp}"
    
    # Firma con HMAC-SHA256 usando App Certificate
    signature = hmac.new(
        AGORA_APP_CERTIFICATE.encode('utf-8'),
        message_to_sign.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    # Encode in base64
    signature_b64 = base64.b64encode(signature).decode('utf-8')
    
    # Format finale: version + signature_b64 + expire_timestamp
    # Format Agora: base64(signature):expire_timestamp
    access_token = f"{signature_b64}:{expire_timestamp}"
    
    return access_token
