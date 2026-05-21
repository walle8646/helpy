# 🚀 Ispiramy — Piattaforma di Consulenze Online

<p align="center">
  <strong>Marketplace per consulenze professionali con video-call, pagamenti e community Q&A</strong>
</p>

---

## 📋 Indice

- [Panoramica](#-panoramica)
- [Funzionalità Principali](#-funzionalità-principali)
- [Stack Tecnologico](#️-stack-tecnologico)
- [Architettura del Progetto](#-architettura-del-progetto)
- [Modelli Dati (Database)](#️-modelli-dati-database)
- [API Endpoints](#-api-endpoints)
- [Variabili d'Ambiente](#-variabili-dambiente)
- [Setup Locale](#️-setup-locale)
- [Deploy con Docker](#-deploy-con-docker)
- [Deploy su Render](#-deploy-su-render)
- [Testing](#-testing)
- [Migrazioni Database](#-migrazioni-database)
- [Documentazione Aggiuntiva](#-documentazione-aggiuntiva)

---

## 🎯 Panoramica

**Ispiramy** è una piattaforma web full-stack che mette in contatto utenti con consulenti professionisti. Gli utenti possono:

- Cercare consulenti per categoria/sottocategoria o tramite ricerca intelligente
- Prenotare consulenze con pagamento Stripe
- Effettuare video-call con registrazione automatica (Agora.io)
- Scambiare messaggi in tempo reale tramite chat widget
- Pubblicare domande nella Community Q&A
- Ricevere notifiche in-app e via email

Il sistema supporta sia SQLite (sviluppo) che PostgreSQL (produzione) ed è containerizzato con Docker per un deploy semplice.

---

## ✨ Funzionalità Principali

### 👤 Gestione Utenti
- **Registrazione** con email + password e conferma via codice a 6 cifre
- **Autenticazione** con JWT (sessione) e fallback session-based
- **Profilo personale** con foto profilo (upload su AWS S3), descrizione, categorie, aree di interesse
- **Modalità anonima** — l'utente può nascondere il proprio nome e apparire come "Utente #ID"
- **Sistema di verifica profili** — quando il profilo soddisfa tutti i requisiti, viene inviata una richiesta ai Verifier/Admin
- **Reset password** via email con codice di conferma

### 🔍 Ricerca Consulenti
- Filtro per **categoria principale e sottocategorie** (struttura gerarchica)
- Filtro per **range di prezzo**
- **Ricerca intelligente** con:
  - Rimozione stop-words italiane
  - Espansione sinonimi (es: "logo" → "grafica", "branding", "design"…)
  - Mapping skill/tool (es: "logo" → "photoshop", "illustrator", "figma"…)
  - **Relevance scoring** che ordina i risultati per pertinenza
- Paginazione risultati (12 per pagina)

### 📅 Sistema Prenotazioni
- I consulenti gestiscono la **disponibilità** tramite blocchi orari su calendario
- I clienti scelgono **data, durata** (30/60/90/120 min) e **slot orario** disponibile
- Prenotazione almeno **4 ore nel futuro**
- **Calcolo automatico prezzo** in base alla tariffa oraria × durata
- Copia disponibilità da un giorno a più giorni target

### 💳 Pagamenti Stripe
- Integrazione **Stripe Checkout** per pagamenti sicuri
- Webhook per conferma automatica del pagamento
- **Rimborso automatico** in caso di rifiuto della consulenza da parte del consulente
- Supporto per prenotazione diretta e tramite offerta di consulenza

### 📹 Video Call (Agora.io)
- Video call in tempo reale tra cliente e consulente
- **Screen sharing** con tracking stato
- **Registrazione automatica** della call su AWS S3 (Agora Cloud Recording)
- **Chat in-call** con supporto allegati (fino a 5 file per messaggio)
- Gestione join/rejoin con lock per evitare race condition
- Validazione tempo della call (fine automatica allo scadere + 5 min di buffer)

### 💬 Messaggistica
- **Chat widget** globale sempre visibile (basso a destra)
- Conversazioni normalizzate (user1_id < user2_id)
- **Polling real-time** per nuovi messaggi (ogni 3-5 secondi)
- **Toast notification** con anteprima messaggio e suono
- **Badge** con contatore messaggi non letti
- Limite di 80 messaggi per conversazione (reset dopo prenotazione confermata)
- Messaggi di sistema per offerte di consulenza

### 🏛️ Community Q&A
- Gli utenti possono **pubblicare domande** (limite: 2 ogni 7 giorni)
- Domande con **categorie e sottocategorie**
- Sistema di **like/upvote** (un like per utente per domanda)
- Contatore **"Messaggia"** (quanti utenti hanno contattato l'autore)
- **Follow** domande per ricevere aggiornamenti
- **Validazione** da parte di admin/verifier prima della pubblicazione
- **Notifica automatica** ai consulenti della stessa categoria quando viene creata una nuova domanda
- Top consulenti suggeriti per categoria

### 🔔 Sistema Notifiche
- **Notifiche in-app** con dropdown campanella
- **Notifiche email** via SendGrid
- Configurazione per tipo (in-app, email, entrambi) tramite tabella `notification_types`
- **Promemoria automatici** — 1 ora e 10 minuti prima dell'appuntamento (APScheduler)
- Tipi di notifica: booking confermato, rifiutato, promemoria, contatto community, messaggio nuovo

### 🎯 Offerte di Consulenza
- Il consulente può inviare un'**offerta personalizzata** a un cliente
- Prezzo e durata custom
- Messaggio automatico nella chat con link per prenotare
- Scadenza automatica dopo 7 giorni
- Il cliente può prenotare tramite l'offerta con pagamento Stripe

---

## ⚙️ Stack Tecnologico

| Componente | Tecnologia |
|---|---|
| **Backend** | Python 3.11 + FastAPI |
| **ORM** | SQLModel (basato su SQLAlchemy) |
| **Database (dev)** | SQLite |
| **Database (prod)** | PostgreSQL |
| **Frontend** | HTML + CSS + JavaScript (Jinja2 templates) |
| **Autenticazione** | JWT (PyJWT) + Sessioni Starlette |
| **Pagamenti** | Stripe (Checkout + Webhooks) |
| **Video Call** | Agora.io (RTC + Cloud Recording) |
| **Email** | SendGrid (API + SMTP) |
| **Storage** | AWS S3 (foto profilo, registrazioni video) |
| **Scheduler** | APScheduler (promemoria automatici) |
| **Logging** | Loguru |
| **Testing** | pytest + httpx |
| **Containerizzazione** | Docker + Docker Compose |
| **Deploy** | Render (Docker) |

---

## 📁 Architettura del Progetto

```
ispiramy/
│
├── app/                          # Codice sorgente principale
│   ├── __init__.py
│   ├── main.py                   # Entry point FastAPI — configura app, middleware, routes
│   ├── models.py                 # Modelli SQLModel (tutte le tabelle del database)
│   ├── database.py               # Configurazione engine DB e session manager
│   ├── logger_config.py          # Configurazione Loguru per il logging
│   ├── scheduler.py              # APScheduler — notifiche programmate (promemoria)
│   ├── mail_confirmation.py      # Invio email conferma registrazione (SMTP)
│   ├── utils_user.py             # Utility utente: hash MD5, codice conferma, display name
│   │
│   ├── routes/                   # Endpoint API e pagine HTML
│   │   ├── home.py               # Homepage con consulenti in evidenza
│   │   ├── auth.py               # Login, registrazione, conferma email, reset password
│   │   ├── user_profile.py       # Profilo personale, upload foto, aggiornamento dati
│   │   ├── public_profile.py     # Profilo pubblico di un utente (/user/{id})
│   │   ├── user_register.py      # Registrazione alternativa (endpoint semplificato)
│   │   ├── consultants.py        # Pagina consulenti con ricerca intelligente e filtri
│   │   ├── messages.py           # Messaggistica: conversazioni, chat, invio messaggi
│   │   ├── community.py          # Community Q&A: domande, like, contatti, follow
│   │   ├── availability.py       # Gestione disponibilità consulenti (calendario)
│   │   ├── booking.py            # Prenotazioni, video call, registrazione, chat in-call
│   │   ├── consultation.py       # Offerte di consulenza personalizzate
│   │   ├── stripe_webhook.py     # Webhook Stripe per conferma pagamenti
│   │   ├── notifications.py      # API notifiche in-app
│   │   └── api.py                # Router API base (prefisso /api)
│   │
│   ├── utils/                    # Utility e servizi
│   │   ├── agora_token.py        # Generazione token Agora RTC per video call
│   │   ├── agora_recording.py    # Agora Cloud Recording: start, stop, gestione S3
│   │   ├── stripe_config.py      # Configurazione Stripe: checkout session, webhook
│   │   ├── email.py              # Invio email verifica e notifiche (SendGrid API)
│   │   ├── notification_manager.py   # Gestore centralizzato notifiche (v1)
│   │   ├── notification_service.py   # Servizio notifiche centralizzato (v2)
│   │   ├── notification_email.py     # Template email per notifiche (HTML inline)
│   │   └── template_helpers.py       # Helper Jinja2: caricamento categorie globale
│   │
│   ├── templates/                # Template HTML (Jinja2)
│   │   ├── base.html             # Layout base con navbar e chat widget
│   │   ├── home.html             # Homepage
│   │   ├── login.html            # Form di login
│   │   ├── register.html         # Form di registrazione
│   │   ├── reset_password.html   # Reset password
│   │   ├── profile.html          # Profilo personale (dashboard)
│   │   ├── user_profile.html     # Profilo pubblico consulente
│   │   ├── consultants.html      # Lista consulenti con filtri
│   │   ├── community.html        # Pagina Community Q&A
│   │   ├── messages_inbox.html   # Inbox messaggi
│   │   ├── chat.html             # Pagina chat dedicata
│   │   ├── chat_widget.html      # Widget chat globale (incluso in base.html)
│   │   ├── booking.html          # Pagina prenotazione consulenza
│   │   ├── booking_success.html  # Conferma pagamento avvenuto
│   │   ├── booking_cancel.html   # Pagamento annullato
│   │   ├── book_consultation_offer.html  # Prenotazione da offerta consulenza
│   │   ├── create_consultation_offer.html  # Form creazione offerta
│   │   ├── availability.html     # Gestione disponibilità calendario
│   │   └── call.html             # Pagina video call
│   │
│   └── static/                   # File statici
│       ├── style.css             # Stile globale
│       ├── consultants.css       # Stile pagina consulenti
│       ├── profile.css           # Stile pagina profilo
│       ├── mobile.css            # Stile responsive mobile
│       └── script.js             # JavaScript globale
│
├── rules/                        # Documentazione tecnica e regole
├── sql_update/                   # Migrazioni SQL e seed data
├── tests/                        # Test automatizzati
├── setup_file/                   # Script di setup iniziale
├── uploads/                      # File caricati (locale)
│
├── Dockerfile                    # Immagine Docker (Python 3.11-slim)
├── docker-compose.yml            # Orchestrazione Docker per sviluppo
├── render.yaml                   # Configurazione deploy Render
├── requirements.txt              # Dipendenze Python
└── README.md                     # Questo file
```

---

## 🗃️ Modelli Dati (Database)

### Tabelle Principali

| Tabella | Descrizione |
|---|---|
| `user` | Utenti e consulenti con profilo completo |
| `category` | Categorie professionali con flag `is_principal` |
| `category_hierarchy` | Relazione gerarchica padre-figlio tra categorie |
| `conversation` | Conversazioni tra coppie di utenti |
| `message` | Messaggi nelle conversazioni |
| `community_questions` | Domande nella Community Q&A |
| `community_likes` | Like/upvote sulle domande |
| `community_contacts` | Traccia chi ha contattato l'autore di una domanda |
| `community_question_follows` | Utenti che seguono una domanda |
| `availability_block` | Blocchi di disponibilità oraria per consulenti |
| `booking` | Prenotazioni con stato, pagamento, call e registrazione |
| `call_messages` | Messaggi durante la video call (con allegati) |
| `consultation_offers` | Offerte personalizzate consulente → cliente |
| `notifications` | Notifiche in-app per utenti |
| `notification_types` | Configurazione tipi notifica (in-app / email) |
| `category_request_notifications` | Notifiche nuove domande per consulenti |
| `configuration_property` | Configurazione globale dell'applicazione |

### Schema User

```
User
├── id, email, password_md5
├── nome, cognome, professione
├── category_id, selected_subcategories (JSON)
├── profile_picture (URL S3)
├── prezzo_consulenza (€/ora)
├── consulenze_vendute, consulenze_acquistate, bollini
├── descrizione, aree_interesse
├── confirmed, is_verified, is_anonymous
├── notify_category_requests
├── user_type_id (1=User, 2=Verifier, 3=Admin)
└── created_at
```

### Schema Booking

```
Booking
├── id, client_user_id, consultant_user_id
├── booking_date, start_time, end_time, duration_minutes
├── status (pending / confirmed / completed / cancelled / no_show)
├── price, payment_status, stripe_checkout_session_id, stripe_payment_intent_id
├── description, client_notes, consultant_notes
├── client_joined_at, consultant_joined_at, call_started_at
├── recording_* (sid, resource_id, status, url, duration, filename...)
├── cancellation_reason, cancelled_by, cancelled_at
└── created_at, updated_at
```

---

## 🌐 API Endpoints

### Autenticazione
| Metodo | Endpoint | Descrizione |
|---|---|---|
| `POST` | `/login` | Login con form HTML |
| `POST` | `/api/login` | Login AJAX (restituisce JWT) |
| `POST` | `/api/register` | Registrazione con invio codice conferma |
| `POST` | `/api/confirm` | Conferma email con codice 6 cifre |
| `GET` | `/logout` | Logout |
| `POST` | `/api/forgot-password` | Richiesta reset password |
| `POST` | `/api/reset-password` | Reset password con codice |

### Profilo
| Metodo | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/profile` | Pagina profilo personale |
| `POST` | `/api/profile/update` | Aggiorna dati profilo |
| `POST` | `/api/upload-profile-picture` | Upload foto profilo su S3 |
| `GET` | `/user/{user_id}` | Profilo pubblico |
| `POST` | `/api/user/set-anonymous` | Attiva/disattiva modalità anonima |
| `GET` | `/api/profile/subcategories/{cat_id}` | Sottocategorie per categoria |

### Consulenti
| Metodo | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/consultants` | Pagina consulenti con filtri e ricerca |

### Messaggistica
| Metodo | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/messaggi` | Inbox messaggi |
| `GET` | `/messaggi/{user_id}` | Chat con utente |
| `GET` | `/api/conversations` | Lista conversazioni |
| `GET` | `/api/messaggi/{user_id}` | Messaggi conversazione |
| `POST` | `/api/messaggi/{user_id}` | Invia messaggio |

### Community Q&A
| Metodo | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/community` | Pagina Community |
| `POST` | `/api/community/ask` | Crea domanda |
| `POST` | `/api/community/like/{id}` | Like/unlike |
| `POST` | `/api/community/contact/{id}` | Traccia contatto |

### Prenotazioni & Video Call
| Metodo | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/book/{consultant_id}` | Pagina prenotazione |
| `GET` | `/api/booking/available-slots/{id}` | Slot disponibili |
| `POST` | `/api/booking/create` | Crea prenotazione (Stripe) |
| `GET` | `/api/booking/my-bookings` | Le mie prenotazioni |
| `GET` | `/api/booking/upcoming` | Prossimi appuntamenti |
| `POST` | `/api/booking/{id}/join` | Partecipa all'appuntamento |
| `GET` | `/api/booking/{id}/agora-token` | Token video call |
| `POST` | `/api/booking/{id}/recording/start-now` | Avvia registrazione |
| `POST` | `/api/booking/{id}/recording/stop` | Ferma registrazione |

### Notifiche
| Metodo | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/notifications` | Lista notifiche |
| `GET` | `/api/notifications/unread/count` | Contatore non lette |
| `POST` | `/api/notifications/{id}/read` | Segna come letta |
| `POST` | `/api/notifications/read-all` | Segna tutte come lette |

### Stripe Webhook
| Metodo | Endpoint | Descrizione |
|---|---|---|
| `POST` | `/webhook/stripe` | Gestione eventi Stripe |

---

## 🔐 Variabili d'Ambiente

Crea un file `.env` nella root del progetto:

```env
# ============ DATABASE ============
DATABASE_URL=sqlite:///./ispiramy.db
# Per PostgreSQL: postgresql://user:password@host:5432/ispiramy_db

# ============ APP ============
SESSION_SECRET=ispiramy-super-secret-key-change-in-production
JWT_SECRET=your-secret-key-change-in-production
BASE_URL=http://localhost:8080
LOG_LEVEL=INFO
PORT=8080

# ============ EMAIL (SendGrid) ============
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.xxxxxxxxxxxxxxxxxxxxxxxx
FROM_EMAIL=noreply@ispiramy.com
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxx
EMAIL_FROM=Ispiramy <noreply@ispiramy.com>

# ============ STRIPE (Pagamenti) ============
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxxxxxxx

# ============ AGORA (Video Call) ============
AGORA_APP_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AGORA_APP_CERTIFICATE=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AGORA_CUSTOMER_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AGORA_CUSTOMER_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ============ AWS S3 (Storage) ============
AWS_ACCESS_KEY_ID=AKIAxxxxxxxxxxxxxxxx
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_S3_BUCKET_NAME=ispiramy-recordings
AWS_S3_REGION=eu-south-1
S3_BUCKET_NAME=ispiramy-images
AWS_REGION=eu-west-1
```

> **Nota**: Il sistema usa l'API HTTP di SendGrid per un invio email più veloce e affidabile. Ottieni la tua API key da https://app.sendgrid.com/settings/api_keys.

---

## 🛠️ Setup Locale

### Prerequisiti
- **Python** 3.11+
- **pip**
- **Docker** e **Docker Compose** (opzionale)

### Installazione

```bash
# 1. Clona il repository
git clone https://github.com/your-org/ispiramy.git
cd ispiramy

# 2. Crea ambiente virtuale
python -m venv venv

# 3. Attiva l'ambiente virtuale
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Installa dipendenze
pip install -r requirements.txt

# 5. Crea il file .env (vedi sezione Variabili d'Ambiente)
cp .env.example .env

# 6. Avvia l'applicazione
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

Apri il browser su **http://localhost:8080**

### Debug in VS Code

Configura `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI (Uvicorn)",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": ["app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8080"],
            "jinja": true,
            "justMyCode": true,
            "envFile": "${workspaceFolder}/.env"
        }
    ]
}
```

---

## 🐳 Deploy con Docker

```bash
# Build e avvio
docker compose up --build

# In background
docker compose up --build -d

# Ferma tutto
docker compose down
```

Il `docker-compose.yml` monta i volumi per hot-reload del codice e dei file caricati.

---

## 🌍 Deploy su Render

Il progetto include un file `render.yaml` per il deploy automatico su [Render](https://render.com):

1. Collega il repository GitHub a Render
2. Configura le variabili d'ambiente nel dashboard Render
3. Il deploy avviene automaticamente ad ogni push

---

## 🧪 Testing

```bash
# Esegui tutti i test
pytest -v

# Test con coverage
pytest --cov=app

# Test specifico
pytest tests/test_api.py -v
pytest tests/test_models.py -v
```

---

## 🔄 Migrazioni Database

Le migrazioni SQL si trovano in `sql_update/`. Ogni migrazione ha versione SQLite e PostgreSQL.

```bash
# SQLite
sqlite3 ispiramy.db < sql_update/migration_add_booking.sql

# PostgreSQL
psql -U postgres -d ispiramy_db -f sql_update/migration_add_booking_postgres.sql
```

### Migrazioni Principali

| Migrazione | Descrizione |
|---|---|
| `migration_add_availability` | Sistema blocchi disponibilità |
| `migration_add_booking` | Sistema prenotazioni |
| `migration_add_recording` | Campi registrazione video |
| `migration_add_stripe_payment` | Campi pagamento Stripe |
| `migration_add_community_likes` | Like community |
| `migration_add_notifications` | Sistema notifiche in-app |
| `migration_add_notification_types` | Configurazione tipi notifica |
| `migration_add_consultation_offers` | Offerte consulenza |
| `migration_add_category_hierarchy` | Categorie gerarchiche |
| `migration_add_is_verified` | Flag verifica profilo |
| `migration_add_is_anonymous` | Modalità anonima |

---

## 📚 Documentazione Aggiuntiva

Nella cartella `rules/`:

| File | Contenuto |
|---|---|
| [ARCHITETTURA.md](rules/ARCHITETTURA.md) | Architettura tecnica dettagliata |
| [API_REFERENCE.md](rules/API_REFERENCE.md) | Riferimento completo API con esempi |
| [DEPLOY_GUIDE.md](rules/DEPLOY_GUIDE.md) | Guida completa al deploy |
| [specifiche.md](rules/specifiche.md) | Specifiche generali del progetto |
| [specifiche_utente_registrazione.md](rules/specifiche_utente_registrazione.md) | Regole registrazione utente |
| [sistema_verifica_profili.md](rules/sistema_verifica_profili.md) | Sistema verifica profili |
| [CHAT_WIDGET_DOCS.md](rules/CHAT_WIDGET_DOCS.md) | Documentazione widget chat |
| [AGORA_RECORDING_SETUP.md](rules/AGORA_RECORDING_SETUP.md) | Setup registrazione video |
| [S3_SETUP.md](rules/S3_SETUP.md) | Configurazione AWS S3 |

---

## 📄 Licenza

Questo progetto è proprietario. Tutti i diritti riservati.

---

<p align="center">
  <em>Realizzato con ❤️ usando FastAPI, Agora.io e Stripe</em>
</p>
