import os

base = "helpy"
files = {
    "app/__init__.py": "",
    "app/main.py": '''from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.logger_config import logger
from app.database import create_db_and_tables
from app.routes import home, api

app = FastAPI(title="helpy")

app.include_router(home.router)
app.include_router(api.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.on_event("startup")
def on_startup():
    logger.info("Avvio applicazione FastAPI")
    create_db_and_tables()
''',
    "app/models.py": '''from sqlmodel import SQLModel, Field

class Example(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    description: str
''',
    "app/database.py": '''from sqlmodel import SQLModel, create_engine, Session
import os
from app.logger_config import logger

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    logger.info("Connessione al database e creazione tabelle se necessario")
    SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)
''',
    "app/logger_config.py": '''from loguru import logger
import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")
logger.remove()
logger.add(lambda msg: print(msg, end=""), level=LOG_LEVEL)
''',
    "app/routes/__init__.py": "",
    "app/routes/home.py": '''from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request, "title": "Home"})
''',
    "app/routes/api.py": '''from fastapi import APIRouter
from app.models import Example
from app.database import get_session
from sqlmodel import select

router = APIRouter(prefix="/api", tags=["api"])

@router.get("/examples", response_model=list[Example])
def get_examples():
    with get_session() as session:
        return session.exec(select(Example)).all()
''',
    "app/templates/home.html": '''<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <h1>Benvenuto in helpy!</h1>
    <p>Questa è la homepage.</p>
    <script src="/static/script.js"></script>
</body>
</html>
''',
    "app/static/style.css": '''body {
    font-family: Arial, sans-serif;
    background: #f8f9fa;
    margin: 0;
    padding: 2rem;
}
''',
    "app/static/script.js": '''console.log("Frontend JS pronto!");
''',
    "tests/test_api.py": '''from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_home():
    response = client.get("/")
    assert response.status_code == 200

def test_get_examples():
    response = client.get("/api/examples")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
''',
    "tests/test_models.py": '''from app.models import Example

def test_example_model():
    e = Example(name="Test", description="Desc")
    assert e.name == "Test"
    assert e.description == "Desc"
''',
    "tests/test_integration.py": '''from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_integration_home():
    response = client.get("/")
    assert response.status_code == 200
''',
    ".env": '''DATABASE_URL=sqlite:///./dev.db
LOG_LEVEL=DEBUG
APP_NAME=helpy
APP_ENV=development
SECRET_KEY=your_secret_key_here
''',
    "Dockerfile": '''FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
''',
    "docker-compose.yml": '''version: "3.9"
services:
  web:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - .:/app
    env_file:
      - .env
''',
    "requirements.txt": '''fastapi==0.110.0
uvicorn==0.29.0
sqlmodel==0.0.16
loguru==0.7.2
jinja2==3.1.3
pytest==8.1.1
httpx==0.27.0
''',
    "README.md": '''# helpy

## Setup locale

```bash
python -m venv venv
source venv/bin/activate  # oppure .\\venv\\Scripts\\activate su Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Docker

```bash
docker compose up --build
```

## Variabili ambiente

Vedi `.env`

## Testing

```bash
pytest -v
```
''',
    "specifiche.md": '''(Copia qui il contenuto del tuo specifiche.md)'''
}

for path, content in files.items():
    full_path = os.path.join(base, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Progetto helpy creato con successo!")