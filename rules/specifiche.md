# specifiche.md

## 🎯 Obiettivo progetto

Questa documentazione definisce le **regole per la creazione iniziale del sito web** basato su **FastAPI**, con frontend HTML/CSS/JS e database SQLite (migrabile a PostgreSQL).
L’obiettivo è predisporre un ambiente di sviluppo solido, containerizzato e pronto per l’estensione futura (autenticazione, API, pagamenti, ecc.).

---

## ⚙️ Stack tecnico

* **Backend**: Python 3.12 + FastAPI
* **Database (locale)**: SQLite → PostgreSQL (in futuro, su Cloud SQL)
* **ORM**: SQLModel (basato su SQLAlchemy)
* **Frontend**: HTML + CSS + JS statici
* **Logging**: Loguru (configurazione in `app/logger_config.py`)
* **Testing**: pytest (unit e integrazione)
* **Containerizzazione**: Docker + Docker Compose
* **Ambiente di sviluppo**: Visual Studio Code
* **Ambiente di produzione (futuro)**: Google Cloud Run + Cloud SQL

---

## 🧩 Architettura cartelle

```
myfastapi-app/
│
├─ app/
│  ├─ main.py
│  ├─ models.py
│  ├─ database.py
│  ├─ routes/
│  │   ├─ __init__.py
│  │   ├─ home.py
│  │   └─ api.py
│  ├─ templates/          # HTML
│  ├─ static/             # CSS / JS
│  ├─ logger_config.py
│  └─ __init__.py
│
├─ tests/
│  ├─ test_api.py
│  ├─ test_models.py
│  └─ test_integration.py
│
├─ .env
├─ Dockerfile
├─ docker-compose.yml
├─ requirements.txt
├─ README.md
└─ specifiche.md
```

---

## 🧱 Database

* Usa **SQLModel** per gestire la connessione e i modelli.
* Tutte le query statiche (se presenti) andranno in `app/sql/` in file `.sql` separati.
* Una sola variabile (`DATABASE_URL`) definirà la connessione.
* In locale: SQLite, con possibilità di passaggio a PostgreSQL modificando `.env`.

### Esempio connessione in `.env`

```
DATABASE_URL=sqlite:///./dev.db
```

Per PostgreSQL:

```
DATABASE_URL=postgresql://user:password@localhost:5432/mydb
```

---

## 🔐 Variabili di ambiente

Definisci tutte le informazioni sensibili o ripetute nel file `.env`, **non versionato** su Git.

### Esempio

```
DATABASE_URL=sqlite:///./dev.db
LOG_LEVEL=DEBUG
APP_NAME=myfastapiapp
APP_ENV=development
SECRET_KEY=your_secret_key_here
```

---

## 🧠 Convenzioni di sviluppo

* Segui il principio **DRY**: sposta funzioni comuni in `utils.py` o in moduli dedicati.
* Usa **type hints** e **Pydantic models** per convalida dati.
* Inserisci docstring per tutte le funzioni e classi principali.
* Ogni endpoint deve avere una breve descrizione e status code.
* Struttura i file in modo chiaro (routes, services, models, templates, static).

---

## 🧰 Logging

* Usa **Loguru** (già configurato in `app/logger_config.py`).
* Aggiungi `logger.info()` e `logger.debug()` in punti chiave:

  * Avvio applicazione.
  * Connessione al database.
  * Chiamate API.
  * Eventuali errori gestiti.

---

## 🧪 Test

* Scrivi test unitari per modelli, API e funzioni principali.
* Scrivi test di integrazione per flussi completi.
* Usa **pytest** + **httpx**.

### Esempi comandi

```bash
pytest -v
pytest --cov=app
```

---

## 📦 Docker

### `Dockerfile`

* Immagine base: `python:3.12-slim`
* Installa dipendenze da `requirements.txt`
* Espone porta `8080`
* Comando di avvio: `uvicorn app.main:app --host 0.0.0.0 --port 8080`

### `docker-compose.yml`

* Servizi:

  * `web`: app FastAPI
  * `db`: database locale (SQLite o PostgreSQL)
  * Volumi: `./data:/data` per file persistenti

---

## 🧭 Ambiente di sviluppo VS Code

* Crea e attiva un ambiente virtuale: `python -m venv venv`
* Installa estensioni:

  * Python
  * Pylance
  * Jinja
  * SQLite Viewer
  * REST Client
* Configura file `.vscode/launch.json` per debug FastAPI.

### Esempio `launch.json`

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI (Uvicorn)",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": ["app.main:app", "--reload"],
            "jinja": true,
            "justMyCode": true
        }
    ]
}
```

---

## 🚀 Avvio locale

### Manuale

```bash
uvicorn app.main:app --reload
```

### Docker Compose

```bash
docker compose up --build
```

Apri il browser su `http://127.0.0.1:8000`

---

## 📘 README

Il README dovrà contenere:

* Istruzioni di setup locale.
* Comandi Docker e Python.
* Variabili `.env` richieste.
* Struttura directory.
* Modalità di avvio e testing.

---

## ✅ Obiettivi Fase 1 (creazione iniziale)

1. Struttura FastAPI completa con SQLite locale funzionante.
2. Frontend HTML/CSS di base collegato a FastAPI.
3. Logging configurato (Loguru).
4. Ambiente virtuale + requirements.txt.
5. Docker e docker-compose pronti.
6. Test base funzionanti.
7. Repository GitHub con istruzioni chiare per sviluppo locale.
