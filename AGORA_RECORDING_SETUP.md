# 🎬 Setup Agora Cloud Recording - Guida Completa

## ✅ CHECKLIST COMPLETAMENTO

### 1. Credenziali AWS (FATTO ✓)
- [x] Account AWS creato
- [x] Bucket S3 creato
- [x] Utente IAM con permessi S3
- [x] Access Key ID e Secret Access Key generate

### 2. Credenziali Agora Cloud Recording (DA FARE ⚠️)

**Devi ottenere Customer ID e Customer Secret da Agora:**

1. Vai su: https://console.agora.io
2. Login con il tuo account Agora
3. Nel menu a sinistra, clicca su **"Products & Usage"**
4. Clicca su **"Cloud Recording"**
5. Troverai:
   - **Customer ID** (es: `4a1b2c3d4e5f6...`)
   - **Customer Secret** (es: `a1b2c3d4e5f6...`)

6. **Aggiungi al file `.env`**:
```properties
AGORA_CUSTOMER_ID=il_tuo_customer_id
AGORA_CUSTOMER_SECRET=il_tuo_customer_secret
```

---

## 📝 CONFIGURAZIONE .env COMPLETA

Il tuo file `.env` dovrebbe avere:

```properties
# Agora.io Video Call Configuration
AGORA_APP_ID=ef8f1bbb0d3b468f9171b3ef17f89df7
AGORA_APP_CERTIFICATE=215cc7280c8643b2897f365463e10a45
AGORA_CUSTOMER_ID=il_tuo_customer_id_qui
AGORA_CUSTOMER_SECRET=il_tuo_customer_secret_qui

# AWS S3 Configuration (per registrazioni video)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=wJalrX...
AWS_S3_BUCKET_NAME=nome-tuo-bucket
AWS_S3_REGION=eu-south-1
```

---

## 🗄️ MIGRATION DATABASE

### SQLite (Sviluppo locale):
```bash
sqlite3 dev.db < migration_add_recording.sql
```

### PostgreSQL (Produzione):
```bash
psql -U postgres -d helpy_db -f migration_add_recording_postgres.sql
```

---

## 🐳 REBUILD DOCKER

Installa le nuove dipendenze:
```bash
docker compose down
docker compose up --build
```

---

## 🧪 TEST FUNZIONAMENTO

1. **Crea una prenotazione** tra cliente e consulente
2. **10 minuti prima** della consulenza, entrambi cliccano "Partecipa"
3. **Cliccano "Inizia Call"**
4. La registrazione **parte automaticamente** quando si uniscono al canale
5. Quando uno termina la call, la registrazione **si ferma automaticamente**
6. Il video viene salvato su S3 e l'URL è disponibile nel database

---

## 📹 COME VEDERE LE REGISTRAZIONI

### Nel database:
```sql
SELECT 
    id,
    recording_status,
    recording_url,
    recording_duration,
    recording_started_at,
    recording_completed_at
FROM booking
WHERE recording_status = 'completed';
```

### API Endpoint:
```
GET /api/booking/{booking_id}/recording
```

Ritorna:
```json
{
    "booking_id": 123,
    "recording_status": "completed",
    "recording_url": "https://helpy-recordings.s3.eu-south-1.amazonaws.com/...",
    "recording_duration": 1800,
    "recording_started_at": "2024-11-05T14:00:00",
    "recording_completed_at": "2024-11-05T14:30:00"
}
```

---

## 💰 COSTI AGORA CLOUD RECORDING

### Free Tier:
- **10.000 minuti/mese** di registrazione GRATIS

### Oltre il Free Tier:
- **$0.99 per 1000 minuti** registrati

### Esempio pratico:
```
100 consulenze × 60 min = 6.000 minuti/mese
→ GRATIS (sotto i 10.000 min)

200 consulenze × 60 min = 12.000 minuti/mese
→ 10.000 gratis + 2.000 a pagamento = $1.98/mese
```

---

## 🔧 TROUBLESHOOTING

### Errore "Customer ID not found":
→ Aggiungi `AGORA_CUSTOMER_ID` e `AGORA_CUSTOMER_SECRET` al `.env`

### Errore "Access Denied" su S3:
→ Verifica che l'utente IAM abbia permessi `s3:PutObject` sul bucket

### Recording non parte:
→ Verifica che entrambi gli utenti abbiano cliccato "Partecipa" (joined_at non null)

### Video non trovato su S3:
→ La registrazione impiega 1-2 minuti per essere processata dopo lo stop

---

## 🚀 PROSSIMI PASSI OPZIONALI

1. **Pagina "Le mie registrazioni"** nel profilo utente
2. **Player video integrato** per vedere i video direttamente in Helpy
3. **Trascrizione automatica** con AWS Transcribe
4. **Notifica email** quando la registrazione è pronta
5. **Download diretto** dei video MP4

---

## 📚 DOCUMENTAZIONE

- Agora Cloud Recording API: https://docs.agora.io/en/cloud-recording/overview/product-overview
- AWS S3 Python SDK (boto3): https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
