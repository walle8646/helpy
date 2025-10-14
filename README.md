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

Vedi `.env`

## Testing

```bash
pytest -v
```
