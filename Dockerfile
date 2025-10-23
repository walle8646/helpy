FROM python:3.11-slim

WORKDIR /app

# Copia requirements
COPY requirements.txt .

# Installa dipendenze
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il codice
COPY . .

# Crea directory uploads se non esiste
RUN mkdir -p /app/uploads/profile_pictures

# Esponi porta (Render usa variabile PORT)
EXPOSE 10000

# Comando avvio (Render passa PORT automaticamente)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}
