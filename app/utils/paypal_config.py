"""
PayPal configuration and utility functions.
Uses PayPal REST API directly via requests (no SDK needed).
"""
import os
import requests
from datetime import datetime, timedelta
from app.logger_config import logger

# PayPal endpoints
PAYPAL_SANDBOX_URL = "https://api-m.sandbox.paypal.com"
PAYPAL_LIVE_URL = "https://api-m.paypal.com"

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
PAYPAL_MODE = os.getenv("PAYPAL_MODE", "sandbox")

_access_token = None
_token_expires_at = None


def _get_base_url():
    return PAYPAL_LIVE_URL if PAYPAL_MODE == "live" else PAYPAL_SANDBOX_URL


def get_access_token():
    """Get OAuth2 access token from PayPal, cached until expiry."""
    global _access_token, _token_expires_at

    if _access_token and _token_expires_at and datetime.utcnow() < _token_expires_at:
        return _access_token

    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        logger.warning("⚠️ PayPal credentials not configured")
        return None

    try:
        resp = requests.post(
            f"{_get_base_url()}/v1/oauth2/token",
            auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
            headers={"Accept": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        _access_token = data["access_token"]
        _token_expires_at = datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600) - 60)
        logger.info(f"✅ PayPal access token ottenuto ({PAYPAL_MODE})")
        return _access_token
    except Exception as e:
        logger.error(f"❌ Errore ottenendo PayPal access token: {e}")
        return None


def _headers():
    token = get_access_token()
    if not token:
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def create_order(amount: float, currency: str, return_url: str, cancel_url: str, metadata: dict = None,
                 intent: str = "CAPTURE"):
    """
    Create a PayPal order. Returns the order dict with approval URL.

    intent="AUTHORIZE" blocca l'importo senza incassarlo: si usa quando il
    consulente deve accettare la richiesta (authorize_order al ritorno da
    PayPal, poi capture_authorization o void_authorization).
    """
    headers = _headers()
    if not headers:
        return None

    body = {
        "intent": intent,
        "purchase_units": [{
            "amount": {
                "currency_code": currency.upper(),
                "value": f"{amount:.2f}",
            },
            "custom_id": str(metadata) if metadata else None,
        }],
        "payment_source": {
            "paypal": {
                "experience_context": {
                    "return_url": return_url,
                    "cancel_url": cancel_url,
                    "brand_name": "Ispiramy",
                    "landing_page": "LOGIN",
                    "user_action": "PAY_NOW",
                }
            }
        }
    }

    try:
        resp = requests.post(f"{_get_base_url()}/v2/checkout/orders", json=body, headers=headers, timeout=15)
        resp.raise_for_status()
        order = resp.json()
        logger.info(f"✅ PayPal order creato: {order['id']}")
        return order
    except Exception as e:
        logger.error(f"❌ Errore creazione PayPal order: {e}")
        return None


def capture_order(order_id: str):
    """
    Capture a previously approved PayPal order. Returns capture details.
    """
    headers = _headers()
    if not headers:
        return None

    try:
        resp = requests.post(
            f"{_get_base_url()}/v2/checkout/orders/{order_id}/capture",
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"✅ PayPal order {order_id} catturato")
        return data
    except Exception as e:
        logger.error(f"❌ Errore cattura PayPal order {order_id}: {e}")
        return None


def authorize_order(order_id: str):
    """Autorizza un ordine approvato con intent AUTHORIZE. Ritorna la risposta di PayPal."""
    headers = _headers()
    if not headers:
        return None
    try:
        resp = requests.post(
            f"{_get_base_url()}/v2/checkout/orders/{order_id}/authorize",
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        logger.info(f"✅ PayPal order {order_id} autorizzato")
        return resp.json()
    except Exception as e:
        logger.error(f"❌ Errore autorizzazione PayPal order {order_id}: {e}")
        return None


def capture_authorization(authorization_id: str):
    """Incassa per intero un importo autorizzato. Ritorna la capture (id, status)."""
    headers = _headers()
    if not headers:
        return None
    try:
        resp = requests.post(
            f"{_get_base_url()}/v2/payments/authorizations/{authorization_id}/capture",
            json={},
            headers={**headers, "Prefer": "return=representation"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"✅ PayPal autorizzazione {authorization_id} incassata: {data.get('id')}")
        return data
    except Exception as e:
        logger.error(f"❌ Errore incasso PayPal autorizzazione {authorization_id}: {e}")
        return None


def void_authorization(authorization_id: str) -> bool:
    """Annulla un'autorizzazione: l'importo bloccato torna disponibile al cliente."""
    headers = _headers()
    if not headers:
        return False
    try:
        resp = requests.post(
            f"{_get_base_url()}/v2/payments/authorizations/{authorization_id}/void",
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        logger.info(f"✅ PayPal autorizzazione {authorization_id} annullata")
        return True
    except Exception as e:
        logger.error(f"❌ Errore annullamento PayPal autorizzazione {authorization_id}: {e}")
        return False


def refund_capture(capture_id: str, amount: float = None, currency: str = "EUR"):
    """
    Refund a captured payment. If amount is None, full refund.
    """
    headers = _headers()
    if not headers:
        return None

    body = {}
    if amount is not None:
        body["amount"] = {
            "currency_code": currency.upper(),
            "value": f"{amount:.2f}",
        }

    try:
        resp = requests.post(
            f"{_get_base_url()}/v2/payments/captures/{capture_id}/refund",
            json=body,
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"✅ PayPal rimborso per capture {capture_id}: {data.get('id')}")
        return data
    except Exception as e:
        logger.error(f"❌ Errore rimborso PayPal capture {capture_id}: {e}")
        return None


def create_payout(recipient_email: str, amount: float, currency: str = "EUR", note: str = "", sender_item_id: str = ""):
    """
    Send a payout to a PayPal account (used for consultant payments).
    """
    headers = _headers()
    if not headers:
        return None

    body = {
        "sender_batch_header": {
            "sender_batch_id": f"ispiramy_{sender_item_id}_{int(datetime.utcnow().timestamp())}",
            "email_subject": "Pagamento ricevuto da Ispiramy",
            "email_message": note or "Hai ricevuto un pagamento per una consulenza su Ispiramy.",
        },
        "items": [{
            "recipient_type": "EMAIL",
            "amount": {
                "currency": currency.upper(),
                "value": f"{amount:.2f}",
            },
            "receiver": recipient_email,
            "note": note,
            "sender_item_id": sender_item_id,
        }]
    }

    try:
        resp = requests.post(f"{_get_base_url()}/v1/payments/payouts", json=body, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        payout_id = data.get("batch_header", {}).get("payout_batch_id")
        logger.info(f"✅ PayPal payout creato: {payout_id} → {recipient_email}")
        return data
    except Exception as e:
        logger.error(f"❌ Errore PayPal payout a {recipient_email}: {e}")
        return None


def verify_webhook_signature(headers_dict: dict, body: bytes, webhook_id: str):
    """
    Verify PayPal webhook signature.
    """
    api_headers = _headers()
    if not api_headers:
        return False

    verify_body = {
        "auth_algo": headers_dict.get("paypal-auth-algo", ""),
        "cert_url": headers_dict.get("paypal-cert-url", ""),
        "transmission_id": headers_dict.get("paypal-transmission-id", ""),
        "transmission_sig": headers_dict.get("paypal-transmission-sig", ""),
        "transmission_time": headers_dict.get("paypal-transmission-time", ""),
        "webhook_id": webhook_id,
        "webhook_event": body if isinstance(body, dict) else {},
    }

    try:
        resp = requests.post(
            f"{_get_base_url()}/v1/notifications/verify-webhook-signature",
            json=verify_body,
            headers=api_headers,
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()
        return result.get("verification_status") == "SUCCESS"
    except Exception as e:
        logger.error(f"❌ Errore verifica webhook PayPal: {e}")
        return False


def is_configured():
    """Check if PayPal is properly configured."""
    return bool(PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET)
