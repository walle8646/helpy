#!/usr/bin/env python3
"""
Script per testare il webhook di Stripe simulando il pagamento
Questo script simula un webhook vero di Stripe
"""
import json
import requests
import hmac
import hashlib
import time
from dotenv import load_dotenv
import os

# Carica le variabili di ambiente
load_dotenv()

# Configurazione
WEBHOOK_URL = "http://localhost:8080/webhook/stripe"
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_86734b95b42eb3b2d41f99e5420b82de2f19e1e854a58c484e28251ceffde621")

print("=" * 70)
print("🧪 STRIPE WEBHOOK TEST - LOCALHOST")
print("=" * 70)

# Dati della sessione checkout (come Stripe li invierebbe)
checkout_session = {
    "id": "cs_test_" + str(int(time.time())),
    "object": "checkout.session",
    "payment_intent": "pi_test_" + str(int(time.time())),
    "metadata": {
        "booking_type": "direct",
        "client_user_id": "19",
        "consultant_user_id": "90",
        "booking_date": "2025-11-20",
        "start_time": "14:00",
        "end_time": "15:00",
        "duration_minutes": "60",
        "availability_block_id": "4",
        "client_notes": "Test booking via webhook"
    }
}

# Evento Stripe
event = {
    "id": "evt_test_" + str(int(time.time())),
    "type": "checkout.session.completed",
    "data": {
        "object": checkout_session
    }
}

# Serializza il payload
payload = json.dumps(event)

# Crea la signature (come Stripe farebbe)
# Formato: timestamp.payload
timestamp = str(int(time.time()))
signed_content = f"{timestamp}.{payload}"
signature = hmac.new(
    WEBHOOK_SECRET.encode('utf-8'),
    signed_content.encode('utf-8'),
    hashlib.sha256
).hexdigest()
stripe_signature = f"t={timestamp},v1={signature}"

print(f"\n� Dettagli Booking:")
print(f"  👤 Client ID: {checkout_session['metadata']['client_user_id']}")
print(f"  💼 Consultant ID: {checkout_session['metadata']['consultant_user_id']}")
print(f"  📅 Data: {checkout_session['metadata']['booking_date']}")
print(f"  ⏰ Ora: {checkout_session['metadata']['start_time']} - {checkout_session['metadata']['end_time']}")
print(f"  ⏱️  Durata: {checkout_session['metadata']['duration_minutes']} minuti")
print(f"  🆔 Session ID: {checkout_session['id']}")

print(f"\n🔐 Firma Webhook:")
print(f"  Secret: {WEBHOOK_SECRET[:30]}...{WEBHOOK_SECRET[-10:]}")
print(f"  Timestamp: {timestamp}")
print(f"  Signature: {stripe_signature[:50]}...\n")

print(f"📤 Inviando a: {WEBHOOK_URL}\n")

# Invia il webhook
try:
    response = requests.post(
        WEBHOOK_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "stripe-signature": stripe_signature
        },
        timeout=10
    )
    
    print(f"✅ Status Code: {response.status_code}")
    
    if response.text:
        try:
            response_json = response.json()
            print(f"📄 Response: {json.dumps(response_json, indent=2)}")
        except:
            print(f"📄 Response: {response.text}")
    
    if response.status_code == 200:
        print("\n" + "=" * 70)
        print("✅ WEBHOOK ELABORATO CON SUCCESSO!")
        print("=" * 70)
        print("\n📍 PROSSIMI STEP:")
        print("1. Controlla il database per verificare se il booking è stato creato")
        print("2. Esegui: sqlite3 dev.db 'SELECT * FROM booking ORDER BY created_at DESC LIMIT 1;'")
        print("3. Oppure controlla le notifiche dell'utente (ID: 90)")
    else:
        print(f"\n❌ Errore HTTP: {response.status_code}")
        
except requests.exceptions.ConnectionError:
    print("❌ Errore: Non riesco a connettermi a localhost:8080")
    print("   Assicurati che il container Docker sia in esecuzione")
    print("   Esegui: docker compose up")
except requests.exceptions.Timeout:
    print("❌ Errore: Timeout della richiesta")
except Exception as e:
    print(f"❌ Errore: {e}")

print("\n" + "=" * 70)
