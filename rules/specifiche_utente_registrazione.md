# specifiche_utente_registrazione.md

## Obiettivo

Regole e specifiche per la creazione della **pagina di registrazione utente** e dei relativi endpoint backend.
L'utente inserisce **email** e **password**, i dati vengono salvati nella tabella `user`; la password deve essere memorizzata come **MD5** (nota di sicurezza sotto). Dopo la registrazione viene generato un codice numerico casuale di 6 cifre, inviato via email e salvato nella tabella `user` in un campo dedicato. L'utente completa la registrazione inserendo il codice; alla conferma il campo `confirmed` (tinyint) viene impostato a `1` (default `0`).

---

## Avvertenza sicurezza

**Importante:** MD5 non è considerato sicuro per l'hashing delle password (è vulnerabile a collisioni e attacchi con rainbow table). È fortemente consigliato usare algoritmi moderni come **bcrypt** o **argon2** in produzione. Qui sotto fornisco comunque le indicazioni richieste per MD5 e, come alternativa consigliata, uno snippet con bcrypt.

---

## Schema della tabella `user` (SQLModel / SQLAlchemy)

Esempio in SQLModel (Python):

```python
from sqlmodel import SQLModel, Field
from typing import Optional

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, nullable=False, unique=True)
    password_md5: str = Field(nullable=False)
    confirmation_code: Optional[str] = Field(default=None, max_length=6)
    confirmed: int = Field(default=0)  # tinyint(1) comportamento
    created_at: Optional[str] = Field(default=None)
```

SQL di esempio (PostgreSQL):

```sql
CREATE TABLE "user" (
  id SERIAL PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  password_md5 CHAR(32) NOT NULL,
  confirmation_code CHAR(6),
  confirmed SMALLINT NOT NULL DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

---

## Variabili d'ambiente necessarie

Inserire queste variabili nel file `.env` (non versionare):

```
DATABASE_URL=sqlite:///./dev.db
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=smtp_user
SMTP_PASSWORD=smtp_password
EMAIL_FROM="MyApp <no-reply@example.com>"
FRONTEND_BASE_URL=http://127.0.0.1:8000
LOG_LEVEL=DEBUG
```

---

## Endpoint richiesti (FastAPI)

1. `GET /register` — serve la pagina HTML del form di registrazione (email + password).
2. `POST /api/register` — accetta JSON `{ "email": "...", "password": "..." }` o form-data; valida, crea utente con `password_md5`, genera codice 6 cifre, salva `confirmation_code` e `confirmed=0`, invia email. Restituisce `201 Created` o errore (es. email già esistente).
3. `POST /api/confirm` — accetta `{ "email": "...", "code": "123456" }`; verifica che il codice corrisponda a quello salvato per l'email; se ok setta `confirmed=1`, cancella o invalida `confirmation_code` e restituisce `200 OK`; altrimenti `400/401`.
4. (Opzionale) `POST /api/resend-code` — ricrea e reinvia un nuovo codice di conferma (con rate limit).

---

## Flujo dettagliato di registrazione

1. Utente apre `/register` e compila email + password; invia il form.
2. Backend valida il formato email e la robustezza minima della password (es. 8 caratteri).
3. Backend verifica che l'email non sia già registrata.
4. Backend calcola l'hash MD5 della password, genera codice di conferma a 6 cifre (stringa con zeri iniziali possibili), salva record: `email`, `password_md5`, `confirmation_code`, `confirmed=0`, `created_at`.
5. Backend invia una mail con il codice (template sotto).
6. Frontend mostra form per inserire codice a 6 cifre (nella stessa pagina o in pagina separata).
7. L'utente inserisce il codice e invia a `/api/confirm`.
8. Backend controlla corrispondenza; se OK imposta `confirmed=1` e risponde successo; altrimenti risponde errore e può permettere retry limitati.

---

## Regole di validazione e controllo

* **Email**: verifica formato con regex e normalizza (lowercase + strip).
* **Password**: almeno 8 caratteri; consigliare complessità (ma non obbligare eccessivamente).
* **Unicità email**: controllo atomico (gestire race condition con unique constraint DB e gestione eccezioni).
* **Codice conferma**: esatto 6 cifre numeriche; scadenza consigliata (es. 24 ore) — salvare timestamp `confirmation_sent_at` se si vuole.
* **Rate limiting**: limitare richieste per IP e per email su endpoint `register`, `resend-code` e `confirm` (es. 5 tentativi / ora).
* **Logging**: loggare eventi importanti con Loguru (registrazione tentata, email inviata, conferma riuscita/fallita).

---

## Email (template)

Oggetto: `Conferma la tua registrazione su MyApp`

Corpo (testo):

```
Ciao,

grazie per esserti registrato su MyApp.
Il tuo codice di conferma è: 123456
Inseriscilo nella pagina di conferma per completare la registrazione.

Se non hai richiesto questa registrazione, ignora questa email.

Grazie,
MyApp Team
```

In HTML: includere chiaramente il codice e istruzioni. Inviare da `EMAIL_FROM`.

---

## Implementazione tecnica: snippet (FastAPI)

### 1) Generazione MD5 (come richiesto)

```python
import hashlib

def hash_md5(password: str) -> str:
    return hashlib.md5(password.encode('utf-8')).hexdigest()
```

### 2) Generazione codice a 6 cifre

```python
import random

def gen_code6() -> str:
    return f"{random.randint(0, 999999):06d}"
```

### 3) Invio email (esempio usando smtplib)

```python
import smtplib
from email.message import EmailMessage

def send_confirmation_email(to_email: str, code: str):
    msg = EmailMessage()
    msg['Subject'] = 'Conferma la tua registrazione su MyApp'
    msg['From'] = EMAIL_FROM
    msg['To'] = to_email
    msg.set_content(f"Ciao\n\nIl tuo codice di conferma è: {code}\n\n")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASSWORD)
        s.send_message(msg)
```

> Nota: gestire eccezioni e retry per fallimenti SMTP, loggare gli errori.

---

## Migrazione e cambiamento futuro (raccomandato)

* Per una sicurezza reale, **sostituire MD5 con bcrypt/argon2** prima del deploy in produzione.
* Esempio bcrypt:

```python
from passlib.hash import bcrypt

# hash
hashed = bcrypt.hash(password)
# verify
bcrypt.verify(password, hashed)
```

* Quando si cambia algoritmo, implementare una migrazione o stored upgrade: ad esempio, aggiungere campo `password_hash` e `hash_algo`, e aggiornare al primo login.

---

## Test richiesti

* **Unit tests**:

  * `hash_md5` produce lunghezza 32 e valori consistenti.
  * `gen_code6` produce stringhe di 6 cifre.
  * Validazione email/password funzionano.
* **Integration tests**:

  * `POST /api/register` crea utente e salva `confirmation_code` e `confirmed=0`.
  * `POST /api/confirm` con codice corretto setta `confirmed=1`.
  * Tentativi con codice errato non confermano.
* Mockare l'invio email nei test (non inviare real emails).

---

## Logging e monitoraggio

* Loggare con `logger.info()` quando: registrazione creata, email inviata, conferma effettuata.
* Loggare con `logger.debug()` dati utili (non password in chiaro!) per debug.
* In caso di errori SMTP o DB, log di livello `error` con stacktrace.

---

## Note operative

* Salvare solo l'hash MD5 della password, **mai** la password in chiaro.
* Non includere l'hash della password nelle risposte API.
* Limitare le informazioni di errore restituite (es. non dire "email esistente" troppo specifico se vuoi prevenire user enumeration — altrimenti rendilo chiaro a UX decisione).

---

## Esempio di API minimal (pseudocodice)

```
POST /api/register
Request: { email, password }
- validate
- if email exists -> 409
- pwd_md5 = hash_md5(password)
- code = gen_code6()
- create user(email, pwd_md5, code, confirmed=0)
- send_confirmation_email(email, code)
- return 201

POST /api/confirm
Request: { email, code }
- find user by email
- if user.confirmation_code == code:
   set user.confirmed = 1
   clear confirmation_code
   return 200
- else return 400

