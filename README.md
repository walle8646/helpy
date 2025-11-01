# helpy

## Setup locale

```bash
python -m venv venv
source venv/bin/activate  # oppure .\venv\Scripts\activate su Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Docker

```bash
docker compose up --build
```

## Variabili ambiente

Crea un file `.env` nella root del progetto copiando `.env.example`:

```bash
cp .env.example .env
```

Configura le seguenti variabili:

### Database
- `DATABASE_URL`: URL del database (SQLite locale o PostgreSQL per produzione)

### JWT Authentication
- `JWT_SECRET`: Chiave segreta per i token JWT (genera una stringa random sicura)

### Email (SendGrid)
- `SENDGRID_API_KEY`: API Key di SendGrid per inviare email via HTTP API
  - Ottieni la tua API key da: https://app.sendgrid.com/settings/api_keys
  - Richiede un account SendGrid (gratuito fino a 100 email/giorno)
- `FROM_EMAIL`: Indirizzo email mittente (deve essere verificato su SendGrid)

### Application
- `BASE_URL`: URL base dell'applicazione (default: http://localhost:8000)

**Nota**: Il sistema ora usa l'API HTTP di SendGrid invece di SMTP per un invio più veloce e affidabile.

## Testing

```bash
pytest -v
```
