# Configurazione AWS S3 per Immagini Profilo

## Panoramica
Il sistema salva le immagini del profilo su **AWS S3** (cloud storage) con fallback a salvataggio locale se S3 non è configurato.

## Come Funziona
1. **Upload**: L'utente carica l'immagine tramite il form di modifica profilo
2. **Validazione**: Il backend valida formato (JPEG, PNG, WebP, GIF) e dimensione (max 5MB)
3. **Salvataggio S3**: L'immagine viene caricata su AWS S3 con nome univoco
4. **Database**: L'URL dell'immagine viene salvato nel campo `profile_picture` dell'utente
5. **Visualizzazione**: L'immagine viene mostrata ovunque nel sito usando l'URL salvato

## Variabili d'Ambiente Necessarie

Aggiungi al file `.env`:

```bash
# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_REGION=eu-west-1  # O la tua regione preferita
S3_BUCKET_NAME=ispiramy-images  # Nome del bucket S3
```

## Setup AWS S3

### 1. Creare un Bucket S3
```bash
# Via AWS Console o AWS CLI
aws s3 mb s3://ispiramy-images --region eu-west-1
```

### 2. Impostare Policy del Bucket (per URL pubblici)
Se vuoi URL pubblici (consigliato):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::ispiramy-images/*"
    }
  ]
}
```

### 3. Creare Credentials AWS (IAM User)
1. Vai su AWS Console → IAM → Users
2. Crea nuovo user "ispiramy-app"
3. Aggiungi permessi: `AmazonS3FullAccess` (o custom policy più restrittiva)
4. Copia `Access Key ID` e `Secret Access Key` nel `.env`

### 4. (Opzionale) Configurare CORS
Se il bucket è privato con signed URLs:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST"],
    "AllowedOrigins": ["https://tuodominio.com", "http://localhost:8080"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3000
  }
]
```

## Flusso Tecnico

### Endpoint: `POST /api/upload-profile-picture`

**Request:**
```bash
curl -X POST http://localhost:8080/api/upload-profile-picture \
  -F "file=@/path/to/image.jpg" \
  -H "Cookie: access_token=..."
```

**Response (Successo):**
```json
{
  "success": true,
  "url": "https://ispiramy-images.s3.eu-west-1.amazonaws.com/profile-pictures/11_20251121_150530.jpg",
  "message": "Immagine caricata con successo!"
}
```

**Response (Errore):**
```json
{
  "error": "Formato file non supportato"
}
```

## Storage Path Structure
```
s3://ispiramy-images/
├── profile-pictures/
│   ├── 11_20251121_150530.jpg
│   ├── 18_20251121_150545.jpg
│   └── ...
```

## Database
Il campo `User.profile_picture` salva:
- **Se S3 è configurato**: URL pubblico o signed URL
  ```
  https://ispiramy-images.s3.eu-west-1.amazonaws.com/profile-pictures/11_20251121_150530.jpg
  ```
- **Se S3 non è configurato**: URL locale
  ```
  /uploads/profile_pictures/11_20251121_150530.jpg
  ```
- **Se nessun file**: `/static/default-avatar.png`

## Visualizzazione nel Sito

### Nel Profilo Utente
```html
<img src="{{ user.profile_picture }}" alt="Profile">
```

### Nella Community
```html
<img src="{{ question.author.profile_picture or '/static/default-avatar.png' }}" 
     alt="Author">
```

### Nel Widget Chat
```javascript
window.openChat(userId, userName, userProfilePicture)
```

## Costi e Performance

### Costi AWS S3
- **Storage**: ~$0.023 USD per GB/mese
- **Richieste GET**: $0.0004 per 10.000 richieste
- **Trasferimento dati**: Generalmente gratuito (download da S3 verso web)

Per una piattaforma di consulenza con 1000 utenti e media 5 immagini per profilo:
- **Storage**: 500MB ≈ $0.01/mese (trascurabile)
- **Richieste**: ~5000 GET/mese ≈ $0.002/mese

### Performance
- **Latenza**: <100ms (CDN globale di AWS)
- **Cache**: 1 anno (immutabile, nomi unici con timestamp)
- **Dimensione**: Massimo 5MB per immagine

## Troubleshooting

### ❌ "AWS credentials not configured"
**Soluzione**: Aggiungi `AWS_ACCESS_KEY_ID` e `AWS_SECRET_ACCESS_KEY` al `.env`

### ❌ "AccessDenied" quando upload su S3
**Soluzione**: Verifica che l'IAM user ha permessi `s3:PutObject` sul bucket

### ❌ URL ritorna 404
**Soluzione**: 
1. Se URL è pubblico: Verifica bucket policy
2. Se URL è signed: Prova a visitare direttamente in browser (scade dopo 1 anno)

### ✅ "Immagine caricata localmente" (fallback)
Significa S3 non è configurato, immagine salvata in `/uploads/profile_pictures/`

## Migration da Salvataggio Locale a S3

Se hai già utenti con immagini locali:

```python
# Uno-off migration script
from app.models import User
from app.database import get_session
import boto3
import os
from pathlib import Path

s3 = boto3.client('s3', 
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'eu-west-1')
)

with get_session() as session:
    users = session.query(User).filter(User.profile_picture.startswith('/uploads/')).all()
    
    for user in users:
        # Leggi immagine locale
        local_path = Path('.' + user.profile_picture)
        if local_path.exists():
            with open(local_path, 'rb') as f:
                # Upload a S3
                s3_key = f"profile-pictures/{user.id}_{local_path.name}"
                s3.put_object(Bucket='ispiramy-images', Key=s3_key, Body=f.read())
                
                # Aggiorna database
                user.profile_picture = f"https://ispiramy-images.s3.eu-west-1.amazonaws.com/{s3_key}"
                session.add(user)
    
    session.commit()
```

## Sicurezza

✅ **Implemented:**
- Validazione del content-type (solo immagini)
- Validazione dimensione file (max 5MB)
- Autenticazione richiesta
- Nomi file unici con timestamp (impossibile sovrascrivere altri utenti)
- Cache control per performance

⚠️ **Considerazioni:**
- Utilizza HTTPS sempre in produzione
- Non salvare dati sensibili su S3 senza encryption
- Monitora usage AWS CloudWatch per anomalie

## Per Sviluppo Locale (senza AWS)

Se non hai AWS configurato, le immagini verranno salvate localmente in:
```
uploads/
└── profile_pictures/
    ├── 11_20251121_150530.jpg
    ├── 18_20251121_150545.jpg
    └── ...
```

E saranno accessibili via URL locale:
```
http://localhost:8080/uploads/profile_pictures/11_20251121_150530.jpg
```

Questo è perfetto per lo sviluppo! Una volta in produzione, configura S3.
