# 🏗️ Architettura Tecnica — Ispiramy

Questo documento descrive l'architettura tecnica dettagliata della piattaforma Ispiramy.

---

## 📊 Diagramma dei Componenti

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT (Browser)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │  Jinja2  │ │   CSS    │ │ JS/AJAX  │ │  Agora Web SDK    │  │
│  │Templates │ │  Styles  │ │  Fetch   │ │  (Video RTC)      │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP / HTTPS
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Application                          │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                     Middleware Layer                       │   │
│  │  ┌─────────────────┐  ┌──────────────────────────────┐   │   │
│  │  │  SessionMiddle   │  │  CategoriesMiddleware        │   │   │
│  │  │  (JWT/Sessions)  │  │  (carica categorie globali)  │   │   │
│  │  └─────────────────┘  └──────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                      Routes Layer                         │   │
│  │  ┌───────┐ ┌──────────┐ ┌───────────┐ ┌──────────────┐  │   │
│  │  │ auth  │ │ booking  │ │ community │ │ messages     │  │   │
│  │  │ home  │ │ consult. │ │ notific.  │ │ profile      │  │   │
│  │  │ avail.│ │ stripe_wh│ │ consultan.│ │ public_prof. │  │   │
│  │  └───────┘ └──────────┘ └───────────┘ └──────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                     Utils / Services                      │   │
│  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  │   │
│  │  │ agora_token  │  │ stripe_config │  │ email        │  │   │
│  │  │ agora_record │  │ notification_ │  │ template_    │  │   │
│  │  │              │  │  service      │  │  helpers     │  │   │
│  │  └──────────────┘  └───────────────┘  └──────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────────────────────┐    │
│  │   APScheduler    │  │   SQLModel ORM                    │    │
│  │  (Background)    │  │   (models.py + database.py)       │    │
│  └──────────────────┘  └──────────┬───────────────────────┘    │
│                                    │                             │
└────────────────────────────────────┼─────────────────────────────┘
                                     │
         ┌───────────────────────────┼──────────────────────────┐
         │                           │                          │
         ▼                           ▼                          ▼
┌─────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   SQLite /      │  │     AWS S3          │  │   Servizi Esterni   │
│   PostgreSQL    │  │  (foto, video)      │  │  ┌──────────────┐  │
│                 │  │                     │  │  │  Stripe API  │  │
│                 │  │                     │  │  │  Agora RTC   │  │
│                 │  │                     │  │  │  SendGrid    │  │
│                 │  │                     │  │  └──────────────┘  │
└─────────────────┘  └─────────────────────┘  └─────────────────────┘
```

---

## 🔄 Flussi Principali

### 1. Flusso di Registrazione e Login

```
Utente → GET /register → Compila form
       → POST /api/register → Backend:
           1. Valida email/password
           2. Hash MD5 password
           3. Genera codice 6 cifre
           4. Salva User (confirmed=0)
           5. Invia email con codice (SendGrid)
       → POST /api/confirm → Backend:
           1. Verifica codice
           2. Imposta confirmed=1
       → POST /api/login → Backend:
           1. Verifica credenziali
           2. Genera JWT
           3. Salva in sessione
           4. Redirect a /profile
```

### 2. Flusso di Prenotazione

```
Cliente → GET /book/{consultant_id} → Pagina prenotazione
        → JS: Seleziona data
        → GET /api/booking/available-slots/{id}?date=...&duration=...
           → Backend calcola slot liberi (disponibilità - prenotazioni)
        → JS: Seleziona slot e compila form
        → POST /api/booking/create
           → Backend: verifica disponibilità, crea Stripe Checkout Session
        → Redirect a Stripe Checkout
        → Stripe processa pagamento
        → POST /webhook/stripe (checkout.session.completed)
           → Backend: crea Booking (status=confirmed, payment=paid)
           → Invia notifica al consulente
           → Schedula promemoria (1h e 10min prima)
        → Redirect a /booking/success
```

### 3. Flusso Video Call

```
Booking confermato → 10 min prima:
  Cliente → POST /api/booking/{id}/join
  Consulente → POST /api/booking/{id}/join
  
  Quando entrambi hanno joinato:
    → Backend prepara recording (status=ready)
  
  GET /api/booking/{id}/agora-token → Token per entrambi
  → Frontend inizializza Agora Web SDK
  → POST /api/booking/{id}/recording/start-now
     → Backend: Agora Cloud Recording API (acquire → start)
  
  Durante la call:
    → Screen sharing (start/stop tracking)
    → Chat in-call con allegati
    → GET /api/booking/{id}/call-status (polling ogni 30s)
  
  Fine call (tempo scaduto o utente termina):
    → POST /api/booking/{id}/recording/stop
       → Backend: Agora API stop → file salvato su S3
    → Booking status → completed
```

### 4. Flusso Community Q&A

```
Utente → GET /community → Vede domande validate
       → POST /api/community/ask
          → Backend: crea domanda (validation=false)
          → Notifica consulenti della categoria
          → Admin/Verifier valida → validation=true
       
Consulente vede notifica → Apre la domanda
  → POST /api/community/contact/{question_id}
     → Backend: traccia contatto, incrementa views
     → Apre chat con l'autore della domanda
```

### 5. Flusso Offerta Consulenza

```
Consulente → GET /consulenza/crea/{client_id}
           → POST con prezzo, durata, messaggio
              → Backend: crea ConsultationOffer
              → Inserisce messaggio di sistema nella chat
              → Il messaggio contiene link: /consulenza/prenota/{offer_id}

Cliente → Click sul link nell'offerta
        → GET /consulenza/prenota/{offer_id}
        → Seleziona slot orario
        → POST /consulenza/prenota/{offer_id}/confirm
           → Redirect a Stripe Checkout
           → Webhook crea Booking con offer_id
```

---

## 🔐 Sistema di Autenticazione

### Dual Auth Strategy

Ispiramy usa un sistema di autenticazione a due livelli:

1. **JWT Token** — Generato al login AJAX, salvato nella sessione Starlette
2. **Session Fallback** — Se il JWT non è presente, controlla `user_id` nella sessione

```python
def verify_token(request: Request) -> Optional[User]:
    # 1. Leggi JWT dalla sessione
    token = request.session.get("access_token")
    if token:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("user_id")
        return session.get(User, user_id)
    
    # 2. Fallback: user_id diretto in sessione
    user_id = request.session.get("user_id")
    if user_id:
        return session.get(User, user_id)
    
    return None
```

### Tipi di Utente

| `user_type_id` | Ruolo | Permessi |
|---|---|---|
| 1 | **User** | Utente base: può cercare, prenotare, chattare, fare domande |
| 2 | **Verifier** | Può verificare profili consulenti |
| 3 | **Admin** | Accesso completo, validazione domande community |

---

## 📦 Gestione Database

### Engine e Sessioni

```python
# database.py
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ispiramy.db")

# Fix automatico per Render: postgres:// → postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, connect_args=connect_args)

@contextmanager
def get_session():
    with Session(engine) as session:
        yield session
```

### Compatibilità SQLite / PostgreSQL

- Tutte le migrazioni hanno doppia versione (`_sqlite.sql` e `_postgres.sql`)
- I campi `time` sono gestiti con `format_time_field()` per compatibilità
- Le query usano `func.date()` per comparazioni date cross-database

---

## 🔔 Sistema Notifiche

### Architettura a 3 Livelli

```
                  ┌─────────────────────────┐
                  │  notification_types DB   │
                  │  (configurazione)        │
                  │  in_app: bool            │
                  │  send_email: bool        │
                  │  email_template: str     │
                  └──────────┬──────────────┘
                             │
                  ┌──────────▼──────────────┐
                  │  notification_service.py │
                  │  send_notification()     │
                  └──────────┬──────────────┘
                             │
              ┌──────────────┼──────────────┐
              │                             │
    ┌─────────▼──────────┐     ┌───────────▼───────────┐
    │ Notifica In-App    │     │ Email SendGrid         │
    │ (tabella notific.) │     │ (notification_email.py)│
    └────────────────────┘     └───────────────────────┘
```

### Tipi di Notifica Configurabili

| type_key | Descrizione | In-App | Email |
|---|---|---|---|
| `booking_confirmed` | Prenotazione confermata | ✅ | ✅ |
| `booking_refused` | Prenotazione rifiutata | ✅ | ✅ |
| `reminder_1h` | Promemoria 1 ora prima | ✅ | ✅ |
| `reminder_10min` | Promemoria 10 minuti prima | ✅ | ✅ |
| `community_contact` | Qualcuno ti ha contattato | ✅ | ✅ |

---

## ⏰ Scheduler (APScheduler)

Lo scheduler gestisce le notifiche programmate con job persistenti nel database.

```python
# Configurazione
jobstores = {
    'default': SQLAlchemyJobStore(url=DATABASE_URL)
}

scheduler = BackgroundScheduler(
    jobstores=jobstores,
    timezone=ZoneInfo("Europe/Rome")
)
```

### Job Schedulati

Per ogni booking confermato vengono creati 4 job:
1. **Promemoria 1h** al cliente
2. **Promemoria 1h** al consulente
3. **Promemoria 10min** al cliente
4. **Promemoria 10min** al consulente

I job sopravvivono ai restart dell'applicazione grazie al `SQLAlchemyJobStore`.

---

## 🔍 Ricerca Intelligente Consulenti

### Pipeline di Ricerca

```
Query utente: "ho bisogno di un logo"
       │
       ▼
1. CLEAN: rimuovi punteggiatura, lowercase
       │
       ▼
2. STOP WORDS: rimuovi articoli, preposizioni italiane
   Risultato: ["bisogno", "logo"]
       │
       ▼
3. SINONIMI: espandi con termini correlati
   "logo" → ["grafica", "branding", "design", "identità", "visiva", ...]
       │
       ▼
4. SKILL MAPPING: espandi con tool/software
   "logo" → ["photoshop", "illustrator", "figma", "canva", ...]
       │
       ▼
5. QUERY DB: ILIKE su nome, cognome, professione, descrizione, aree_interesse
       │
       ▼
6. SCORING: calcola punteggio per ogni risultato
   - +10 punti per keyword originale trovata
   - +5 punti per keyword espansa trovata
   - +3 punti se match nella professione
   - +2 punti per bollino
   - +1 punto per consulenza venduta
       │
       ▼
7. ORDINAMENTO per score decrescente → paginazione
```

---

## 📹 Integrazione Agora

### Componenti

| Componente | Uso | Credenziali |
|---|---|---|
| **Agora Web SDK** | Video/audio in tempo reale nel browser | App ID + Token RTC |
| **Agora Cloud Recording** | Registrazione server-side su S3 | Customer ID + Customer Secret |
| **Token Builder** | Genera token RTC con scadenza | App Certificate |

### Flusso Registrazione

```
1. join_booking() → genera token, status = "ready"
2. Frontend entra nel canale Agora
3. Frontend chiama start-now → Backend:
   a. acquire() → ottieni resource_id
   b. start() → avvia recording con config S3
   c. status = "recording"
4. Fine call → stop() → Agora salva su S3
5. Backend salva URL nel booking
```

### Configurazione S3 per Recording

Il file viene salvato con nome: `booking_{id}_{timestamp}_session{n}`

Regioni AWS mappate a codici Agora per ottimizzare la latenza.

---

## 💳 Integrazione Stripe

### Flusso Pagamento

```
1. Frontend → POST /api/booking/create con dati prenotazione
2. Backend → stripe.checkout.Session.create(
     amount_cents, currency='eur',
     success_url, cancel_url,
     metadata={booking details}
   )
3. Backend risponde con checkout_url
4. Frontend redirect → Stripe Checkout hosted page
5. Utente completa il pagamento
6. Stripe → POST /webhook/stripe (evento: checkout.session.completed)
7. Backend legge metadata → crea Booking nel DB
8. Invia notifiche + schedula promemoria
```

### Rimborsi

Quando il consulente rifiuta una prenotazione (`POST /api/booking/{id}/refuse`):

```python
stripe.Refund.create(
    payment_intent=booking.stripe_payment_intent_id,
    reason='requested_by_customer'
)
```

---

## 📧 Sistema Email

### Provider: SendGrid

Due modalità di invio:
1. **API HTTP** (preferita) — `SendGridAPIClient` per email notifiche
2. **SMTP** — Fallback per email conferma registrazione

### Template Email

I template sono definiti inline in `notification_email.py` come stringhe HTML con placeholder `{variable}`.

Template disponibili:
- `booking_confirmed.html` — Conferma prenotazione
- `booking_refused.html` — Prenotazione rifiutata
- `booking_reminder_1h.html` — Promemoria 1 ora
- `booking_reminder_10min.html` — Promemoria 10 minuti
- `community_contact.html` — Contatto dalla community

---

## 🗄️ Categorie Gerarchiche

### Struttura

```
Categoria Principale (is_principal=true)
├── Sottocategoria 1
├── Sottocategoria 2
└── Sottocategoria 3
```

La relazione è gestita dalla tabella `category_hierarchy`:

```sql
category_hierarchy
├── parent_category_id  →  category.id (principale)
├── child_category_id   →  category.id (sottocategoria)
└── position            →  ordine di visualizzazione
```

Gli utenti selezionano:
- **Una categoria principale** (`user.category_id`)
- **Più sottocategorie** (`user.selected_subcategories` come JSON array)

---

## 🔒 Sicurezza

### Note sulla Sicurezza Attuale

| Area | Stato | Note |
|---|---|---|
| Password hashing | ⚠️ MD5 | Da migrare a bcrypt/argon2 in produzione |
| Autenticazione | ✅ JWT | Token con scadenza 7 giorni |
| Sessioni | ✅ Starlette | Cookie httpOnly con secret key |
| XSS | ✅ | Escape HTML nei messaggi chat |
| CSRF | ⚠️ Parziale | Da implementare token CSRF per i form |
| Rate limiting | ⚠️ Non impl. | Consigliato per endpoint sensibili |
| Upload file | ✅ | Validazione tipo e dimensione (max 5MB) |
| SQL Injection | ✅ | Protetto da SQLModel/SQLAlchemy ORM |
| Stripe webhook | ✅ | Verifica firma webhook |

### Raccomandazioni per Produzione

1. Sostituire MD5 con **bcrypt** per le password
2. Implementare **rate limiting** su login, registrazione, invio messaggi
3. Aggiungere **CSRF token** ai form
4. Configurare **CORS** appropriatamente
5. Usare **HTTPS** obbligatorio
6. Ruotare i **JWT secret** periodicamente
7. Implementare **2FA** per account sensibili
