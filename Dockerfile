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

# Comando avvio (Render passa PORT automaticamente).
# Render chiude l'HTTPS sul proprio proxy e inoltra all'app in HTTP: senza
# --forwarded-allow-ips uvicorn ignora X-Forwarded-Proto/For (di default si fida
# solo di 127.0.0.1), l'app crede di essere in HTTP e vede come client l'IP del
# proxy. '*' è sicuro solo perché su Render il container è raggiungibile
# esclusivamente attraverso il proxy.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers --forwarded-allow-ips='*'
