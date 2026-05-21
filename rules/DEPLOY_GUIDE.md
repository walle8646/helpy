# 🚀 Guida al Deploy — Ispiramy

Guida completa per il deploy di Ispiramy in ambiente locale, Docker e produzione (Render).

---

## 📋 Indice

- [Prerequisiti](#prerequisiti)
- [Setup Locale (Sviluppo)](#-setup-locale-sviluppo)
- [Docker (Sviluppo/Staging)](#-docker-sviluppostaging)
- [Deploy su Render (Produzione)](#-deploy-su-render-produzione)
- [Variabili d'Ambiente](#-variabili-dambiente)
- [Configurazione Servizi Esterni](#-configurazione-servizi-esterni)
- [Migrazione Database](#-migrazione-database)
- [Troubleshooting](#-troubleshooting)

---

## Prerequisiti

| Requisito | Versione Minima | Note |
|---|---|---|
| Python | 3.11+ | Raccomandato 3.11 |
| pip | 23+ | Gestore pacchetti Python |
| PostgreSQL | 14+ | Solo per produzione |
| Docker | 20+ | Opzionale, per deploy containerizzato |
| Docker Compose | 2+ | Opzionale |
| Git | 2+ | Version control |

### Account servizi esterni (per funzionalità complete)

- **Stripe** — Pagamenti ([dashboard.stripe.com](https://dashboard.stripe.com))
- **Agora.io** — Video call ([console.agora.io](https://console.agora.io))
- **SendGrid** — Email ([app.sendgrid.com](https://app.sendgrid.com))
- **AWS S3** — Storage file ([aws.amazon.com/s3](https://aws.amazon.com/s3))

---

## 💻 Setup Locale (Sviluppo)

### 1. Clona il repository

```bash
git clone https://github.com/your-username/ispiramy.git
cd ispiramy
```

### 2. Crea ambiente virtuale

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Installa dipendenze

```bash
pip install -r requirements.txt
```

### 4. Configura variabili d'ambiente

Crea un file `.env` nella root del progetto:

```env
# === Database (SQLite per sviluppo) ===
DATABASE_URL=sqlite:///./ispiramy.db

# === Sicurezza ===
JWT_SECRET=your-secret-key-change-in-production
SESSION_SECRET=your-session-secret-change-in-production

# === Stripe (modalità test) ===
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_30=price_...
STRIPE_PRICE_60=price_...
STRIPE_PRICE_90=price_...
STRIPE_PRICE_120=price_...

# === Agora.io ===
AGORA_APP_ID=your_agora_app_id
AGORA_APP_CERTIFICATE=your_agora_app_certificate
AGORA_CUSTOMER_ID=your_agora_customer_id
AGORA_CUSTOMER_SECRET=your_agora_customer_secret

# === AWS S3 ===
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_S3_BUCKET=your-bucket-name
AWS_S3_REGION=eu-south-1
S3_BUCKET_NAME=your-bucket-name

# === SendGrid ===
SENDGRID_API_KEY=SG.your_sendgrid_api_key
FROM_EMAIL=noreply@yourdomain.com

# === App ===
BASE_URL=http://localhost:10000
PORT=10000
```

### 5. Avvia l'applicazione

```bash
uvicorn app.main:app --host 0.0.0.0 --port 10000 --reload
```

L'app sarà disponibile su: **http://localhost:10000**

### 6. (Opzionale) Setup Stripe Webhook locale

Per testare i webhook Stripe in locale, usa [Stripe CLI](https://stripe.com/docs/stripe-cli):

```bash
# Installa Stripe CLI e autenticati
stripe login

# Forwarda i webhook alla tua app locale
stripe listen --forward-to localhost:10000/webhook/stripe
```

Copia il webhook signing secret (`whsec_...`) nel tuo `.env`.

---

## 🐳 Docker (Sviluppo/Staging)

### Build e avvio con Docker Compose

```bash
# Build dell'immagine e avvio
docker-compose up --build

# In background
docker-compose up --build -d

# Controlla i log
docker-compose logs -f

# Stop
docker-compose down
```

### Dockerfile

Il Dockerfile usa Python 3.11-slim:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 10000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
```

### docker-compose.yml

Configurazione con PostgreSQL incluso:

```yaml
version: "3.8"
services:
  web:
    build: .
    ports:
      - "10000:10000"
    environment:
      - DATABASE_URL=postgresql://ispiramy:ispiramy@db:5432/ispiramy
      # ... altre variabili d'ambiente
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=ispiramy
      - POSTGRES_PASSWORD=ispiramy
      - POSTGRES_DB=ispiramy
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

### Comandi utili Docker

```bash
# Entra nel container
docker-compose exec web bash

# Esegui una migrazione SQL
docker-compose exec db psql -U ispiramy -d ispiramy -f /path/to/migration.sql

# Backup database
docker-compose exec db pg_dump -U ispiramy ispiramy > backup.sql

# Restore database
docker-compose exec db psql -U ispiramy ispiramy < backup.sql
```

---

## ☁️ Deploy su Render (Produzione)

### 1. Configurazione Render

Il progetto include un `render.yaml` (Blueprint) per il deploy automatico:

```yaml
services:
  - type: web
    name: ispiramy
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: ispiramy-db
          property: connectionString
      # ... altre variabili

databases:
  - name: ispiramy-db
    plan: free
    databaseName: ispiramy
    user: ispiramy
```

### 2. Deploy Manuale

1. **Crea account su [render.com](https://render.com)**
2. **Connetti il tuo repository GitHub**
3. **Crea un nuovo Web Service**:
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. **Crea un database PostgreSQL** su Render
5. **Configura le variabili d'ambiente** (vedi sezione sotto)

### 3. Deploy con Blueprint

1. Vai su [Render Dashboard](https://dashboard.render.com)
2. Click su **Blueprints** → **New Blueprint Instance**
3. Seleziona il repository con il `render.yaml`
4. Render creerà automaticamente il servizio web + database
5. Configura le variabili d'ambiente mancanti

### 4. Variabili d'Ambiente su Render

Vai su **Web Service** → **Environment** → **Environment Variables**:

⚠️ **IMPORTANTE**: Render genera automaticamente `DATABASE_URL` con prefisso `postgres://`. Il codice di Ispiramy lo converte automaticamente in `postgresql://`.

### 5. Database PostgreSQL su Render

Una volta creato il database, Render fornisce:
- **Internal Connection String** — Per i servizi Render nella stessa regione
- **External Connection String** — Per accesso esterno (utile per migrazioni)

Usa la **Internal Connection String** come `DATABASE_URL` per performance ottimali.

### 6. Esecuzione Migrazioni su Render

Puoi eseguire le migrazioni SQL connettendoti al database esterno:

```bash
# Dalla tua macchina locale
psql "CONNECTION_STRING_ESTERNA" -f sql_update/migration_file.sql
```

Oppure tramite la **Shell** di Render (disponibile nella dashboard del servizio).

---

## 🔧 Variabili d'Ambiente

### Tabella Completa

| Variabile | Obbligatoria | Default | Descrizione |
|---|---|---|---|
| `DATABASE_URL` | ✅ | `sqlite:///./ispiramy.db` | Stringa di connessione database |
| `JWT_SECRET` | ✅ | — | Secret per generazione JWT |
| `SESSION_SECRET` | ✅ | — | Secret per sessioni Starlette |
| `PORT` | ❌ | `10000` | Porta del server |
| `BASE_URL` | ✅ | — | URL base dell'app (per link nelle email) |
| `STRIPE_SECRET_KEY` | ✅* | — | Chiave segreta Stripe |
| `STRIPE_PUBLISHABLE_KEY` | ✅* | — | Chiave pubblica Stripe |
| `STRIPE_WEBHOOK_SECRET` | ✅* | — | Secret per verifica webhook Stripe |
| `STRIPE_PRICE_30` | ✅* | — | ID prezzo Stripe per 30 min |
| `STRIPE_PRICE_60` | ✅* | — | ID prezzo Stripe per 60 min |
| `STRIPE_PRICE_90` | ✅* | — | ID prezzo Stripe per 90 min |
| `STRIPE_PRICE_120` | ✅* | — | ID prezzo Stripe per 120 min |
| `AGORA_APP_ID` | ✅* | — | App ID di Agora.io |
| `AGORA_APP_CERTIFICATE` | ✅* | — | Certificate di Agora.io |
| `AGORA_CUSTOMER_ID` | ❌ | — | Customer ID per Agora Cloud Recording |
| `AGORA_CUSTOMER_SECRET` | ❌ | — | Customer Secret per Agora Cloud Recording |
| `AWS_ACCESS_KEY_ID` | ✅* | — | AWS Access Key |
| `AWS_SECRET_ACCESS_KEY` | ✅* | — | AWS Secret Key |
| `AWS_S3_BUCKET` | ✅* | — | Nome bucket S3 |
| `AWS_S3_REGION` | ❌ | `eu-south-1` | Regione AWS |
| `S3_BUCKET_NAME` | ✅* | — | Bucket per le registrazioni |
| `SENDGRID_API_KEY` | ✅* | — | API Key SendGrid |
| `FROM_EMAIL` | ✅* | — | Email mittente |

> \* Obbligatoria per la funzionalità specifica. L'app si avvia anche senza, ma la funzionalità sarà disabilitata.

---

## 🔌 Configurazione Servizi Esterni

### Stripe

1. Vai su [Stripe Dashboard](https://dashboard.stripe.com)
2. Copia le chiavi da **Developers** → **API Keys**
3. Crea i **Products** con i 4 prezzi (30/60/90/120 min)
4. Per i webhook:
   - Vai su **Developers** → **Webhooks**
   - Aggiungi endpoint: `https://your-domain.com/webhook/stripe`
   - Seleziona evento: `checkout.session.completed`
   - Copia il **Signing Secret**

> Per maggiori dettagli, vedi la sezione Stripe nel README.

### Agora.io

1. Vai su [Agora Console](https://console.agora.io)
2. Crea un nuovo progetto
3. Copia **App ID** e **App Certificate**
4. Per Cloud Recording:
   - Attiva il servizio **Cloud Recording** nel progetto
   - Genera **Customer ID** e **Customer Secret** in **RESTful API**

> Per la configurazione dettagliata della registrazione, vedi [AGORA_RECORDING_SETUP.md](AGORA_RECORDING_SETUP.md).

### AWS S3

1. Crea un bucket S3 nella regione preferita
2. Configura le policy CORS per il bucket:
   ```json
   [
     {
       "AllowedHeaders": ["*"],
       "AllowedMethods": ["GET", "PUT", "POST"],
       "AllowedOrigins": ["*"],
       "ExposeHeaders": []
     }
   ]
   ```
3. Crea un utente IAM con accesso S3
4. Genera Access Key e Secret Key

> Per la configurazione dettagliata, vedi [S3_SETUP.md](S3_SETUP.md).

### SendGrid

1. Vai su [SendGrid](https://app.sendgrid.com)
2. Crea una **API Key** con permesso **Mail Send**
3. Configura il **Sender Authentication** per il tuo dominio
4. Imposta `FROM_EMAIL` con un indirizzo verificato

---

## 🗃️ Migrazione Database

### Da SQLite a PostgreSQL

Quando passi dallo sviluppo (SQLite) alla produzione (PostgreSQL):

1. **Crea le tabelle** — L'app le crea automaticamente all'avvio con `create_db_and_tables()`

2. **Esegui le migrazioni** — Usa i file `_postgres.sql` nella cartella `sql_update/`:

```bash
# Esempio: esegui tutte le migrazioni necessarie
psql $DATABASE_URL -f sql_update/migration_add_availability_postgres.sql
psql $DATABASE_URL -f sql_update/migration_add_booking_postgres.sql
psql $DATABASE_URL -f sql_update/migration_add_community_contacts_postgres.sql
psql $DATABASE_URL -f sql_update/migration_add_community_likes_postgres.sql
psql $DATABASE_URL -f sql_update/migration_add_consultation_offers_postgres.sql
psql $DATABASE_URL -f sql_update/migration_add_configuration_property_postgres.sql
# ... continua con tutte le migrazioni necessarie
```

3. **Inserisci dati iniziali** — Categorie e dati di base:

```bash
psql $DATABASE_URL -f sql_update/insert_new_categories_with_hierarchy_postgres.sql
psql $DATABASE_URL -f sql_update/insert_community_questions_postgres.sql
psql $DATABASE_URL -f sql_update/insert_dummy_users_postgres.sql  # solo per test
```

### Ordine Consigliato delle Migrazioni

1. Migrazioni strutturali (tabelle, colonne)
2. Migrazioni per la gerarchia delle categorie
3. Insert dati iniziali (categorie, tipi di notifica)
4. Insert dati di test (opzionale)

### Applicare una Migrazione Completa

Per applicare tutte le migrazioni in un colpo solo su SQLite:

```bash
sqlite3 ispiramy.db < sql_update/apply_full_update_sqlite.sql
```

---

## 🔍 Troubleshooting

### Problemi Comuni

#### L'app non si avvia

```
Error: ModuleNotFoundError: No module named 'app'
```
**Soluzione**: Assicurati di essere nella directory root del progetto e di avere attivato il venv.

---

#### Errore connessione database

```
sqlalchemy.exc.OperationalError: could not connect to server
```
**Soluzione**: Verifica che il `DATABASE_URL` sia corretto e che il database sia raggiungibile.

---

#### Errore S3 all'avvio

```
WARNING - S3 credentials test failed
```
**Soluzione**: Non è bloccante. L'app funziona senza S3, ma upload foto e registrazioni non funzioneranno. Verifica le credenziali AWS.

---

#### Template non trovato

```
jinja2.exceptions.TemplateNotFound
```
**Soluzione**: Verifica che la directory `app/templates/` contenga tutti i template. Il path è relativo alla root del progetto.

---

#### Stripe webhook fallisce

```
stripe.error.SignatureVerificationError
```
**Soluzione**: Verifica che `STRIPE_WEBHOOK_SECRET` corrisponda al secret dell'endpoint webhook configurato su Stripe. In locale, usa il secret fornito da `stripe listen`.

---

#### APScheduler non parte

```
ERROR - Errore avvio scheduler
```
**Soluzione**: Potrebbe essere un conflitto di job store. Prova a cancellare i job orfani dal database o riavvia con un database pulito.

---

#### Port già in uso

```
ERROR: [Errno 98] Address already in use
```
**Soluzione**: 
```bash
# Trova il processo che usa la porta
# Linux/macOS
lsof -i :10000
kill -9 <PID>

# Windows
netstat -ano | findstr :10000
taskkill /PID <PID> /F
```

---

### Log e Debug

L'app usa **Loguru** per il logging. I log sono configurati in `app/logger_config.py`:

- **Console**: Tutti i log vengono stampati su stdout
- **Livelli**: DEBUG (sviluppo), INFO (produzione)

Per abilitare il debug dettagliato:

```bash
# Avvia con reload e log verbosi
uvicorn app.main:app --host 0.0.0.0 --port 10000 --reload --log-level debug
```

---

### Checklist Pre-Deploy

- [ ] Tutte le variabili d'ambiente sono configurate
- [ ] Il database è accessibile
- [ ] Le migrazioni SQL sono state applicate
- [ ] I prodotti Stripe sono stati creati (4 durate)
- [ ] Il webhook Stripe è configurato con l'URL di produzione
- [ ] Il bucket S3 ha le CORS corrette
- [ ] L'email SendGrid è verificata
- [ ] Il progetto Agora è attivo
- [ ] `JWT_SECRET` e `SESSION_SECRET` sono valori sicuri e unici
- [ ] L'app risponde correttamente all'endpoint `/health`
