"""
Stripe configuration and utility functions
"""
import os
from dotenv import load_dotenv

# Force reload environment variables
load_dotenv(override=True)

# Import stripe module
try:
    import stripe
    stripe_module = stripe
    print("✅ Stripe module imported successfully")
    print(f"✅ Stripe module is: {stripe_module}")
except ImportError as e:
    print(f"⚠️ WARNING: Stripe package is not installed: {e}")
    stripe_module = None
    stripe = None

# Get Stripe secret key
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Initialize Stripe only if module and key are available
if stripe and STRIPE_SECRET_KEY:
    print(f"🔑 Initializing Stripe with key: {STRIPE_SECRET_KEY[:20]}...")
    stripe.api_key = STRIPE_SECRET_KEY
    print(f"✅ Stripe API key set successfully: {stripe.api_key[:20] if stripe.api_key else 'NONE'}")
    print(f"✅ Stripe module after init: {stripe}")
elif not stripe:
    print("⚠️ Stripe module not available - payment features disabled")
elif not STRIPE_SECRET_KEY:
    print("⚠️ STRIPE_SECRET_KEY not found - payment features disabled")
APP_URL = os.getenv("BASE_URL", "http://localhost:8000")

def get_stripe_publishable_key():
    """Return the Stripe publishable key for frontend use"""
    return STRIPE_PUBLISHABLE_KEY

def create_checkout_session(
    amount: int,  # Amount in cents (e.g., 5000 = €50.00)
    currency: str,
    success_url: str,
    cancel_url: str,
    metadata: dict = None
):
    """
    Create a Stripe Checkout Session
    
    Args:
        amount: Amount in cents
        currency: Currency code (e.g., 'eur', 'usd')
        success_url: URL to redirect after successful payment
        cancel_url: URL to redirect if payment is cancelled
        metadata: Additional data to store with the session
    
    Returns:
        Stripe Checkout Session object
    """
    if not stripe:
        raise RuntimeError("Stripe module not available. Cannot create checkout session.")
    
    if not STRIPE_SECRET_KEY:
        raise RuntimeError("Stripe is not configured. Missing STRIPE_SECRET_KEY.")
    
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': currency,
                    'unit_amount': amount,
                    'product_data': {
                        'name': 'Consulenza',
                        'description': 'Prenotazione consulenza con esperto',
                    },
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata or {},
        )
        return session
    except Exception as e:
        print(f"Error creating Stripe session: {e}")
        raise

def construct_webhook_event(payload: bytes, signature: str):
    """
    Verify and construct a Stripe webhook event
    
    Args:
        payload: Raw request body
        signature: Stripe signature from headers
    
    Returns:
        Stripe Event object
    """
    if not stripe:
        raise RuntimeError("Stripe module not available. Cannot process webhook.")
    
    if not STRIPE_WEBHOOK_SECRET:
        raise RuntimeError("Stripe webhook secret not configured.")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, STRIPE_WEBHOOK_SECRET
        )
        return event
    except ValueError as e:
        # Invalid payload
        raise ValueError(f"Invalid payload: {e}")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise ValueError(f"Invalid signature: {e}")
