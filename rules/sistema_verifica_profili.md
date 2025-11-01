# Sistema di Verifica Profili

## Overview
Quando un utente modifica il proprio profilo e soddisfa tutti i criteri di qualità, viene inviata automaticamente una email agli utenti con ruolo **Verifier** (user_type_id=2) e **Admin** (user_type_id=3) per richiedere la verifica del profilo.

## Criteri per la Richiesta di Verifica

Un profilo è idoneo per la verifica quando **tutti** i seguenti campi sono compilati correttamente:

1. ✅ **Professione** (`professione`) - deve essere compilata e non vuota
2. ✅ **Categoria** (`category_id`) - deve essere selezionata una categoria
3. ✅ **Aree di Interesse** (`aree_interesse`) - deve essere compilata e non vuota
4. ✅ **Descrizione** (`descrizione`) - deve contenere **almeno 200 caratteri**

## Funzionalità Implementate

### 1. Character Counter (Contatore Caratteri)
- **Posizione**: Campo "Descrizione" nel form di modifica profilo (`/profile`)
- **Comportamento**:
  - Mostra conteggio in tempo reale: `X/200 caratteri`
  - **Rosso** (<200 caratteri): Mostra quanti caratteri mancano
  - **Verde** (≥200 caratteri): Conferma che il requisito è soddisfatto
  - Si aggiorna ad ogni carattere digitato

**File modificato**: `app/templates/profile.html`
```html
<label>Descrizione <span id="charCounter">0/200 caratteri</span></label>
<textarea id="descrizioneTextarea" name="descrizione" rows="5">...</textarea>
<small id="descrizioneHint">La descrizione deve essere di almeno 200 caratteri...</small>
```

**JavaScript**: Aggiorna contatore e colore dinamicamente

### 2. Email Notification System
Quando il profilo soddisfa tutti i criteri:
- Viene inviata una email a tutti gli utenti con `user_type_id IN (2, 3)`
- L'email contiene:
  - Nome e email dell'utente
  - Conferma che tutti i requisiti sono soddisfatti
  - Link diretto al profilo utente per la revisione
  - ID utente per riferimento

**File creato**: `app/utils/email.py` → funzione `send_profile_verification_request()`

**File modificato**: `app/routes/user_profile.py`
```python
# Logica implementata nel route @router.post("/api/profile/update")
if profile_complete and not was_verified_before:
    verifiers = session.exec(select(User).where(User.user_type_id.in_([2, 3]))).all()
    for verifier in verifiers:
        send_profile_verification_request(...)
```

### 3. User Feedback
- Dopo l'aggiornamento del profilo, se i criteri sono soddisfatti, l'utente vede un messaggio:
  > **"Profilo aggiornato con successo! ✨ Il tuo profilo è stato inviato per la verifica. Riceverai una notifica quando sarà approvato."**

**File modificato**: `app/templates/profile.html` (JavaScript nel form submit handler)

## Database Schema

### Tabella `user_type`
```sql
CREATE TABLE user_type (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

INSERT INTO user_type (id, name) VALUES
(1, 'User'),
(2, 'Verifier'),
(3, 'Admin');
```

### Colonne aggiunte a `user`
```sql
ALTER TABLE user ADD COLUMN is_verified BOOLEAN DEFAULT 0;
ALTER TABLE user ADD COLUMN user_type_id INTEGER DEFAULT 1;
```

**File di migrazione**:
- `migration_add_is_verified.sql` (SQLite)
- `migration_add_is_verified_postgres.sql` (PostgreSQL)

## Workflow Completo

### 1. Utente Modifica Profilo
1. Accede a `/profile`
2. Compila i campi: professione, categoria, aree interesse, descrizione
3. Vede il contatore caratteri diventare verde quando raggiunge 200+
4. Salva il profilo

### 2. Backend Verifica Criteri
```python
profile_complete = (
    db_user.professione and db_user.professione.strip() != "" and
    db_user.category_id is not None and
    db_user.aree_interesse and db_user.aree_interesse.strip() != "" and
    db_user.descrizione and len(db_user.descrizione.strip()) >= 200
)
```

### 3. Invio Email ai Verifiers
- Query: `SELECT * FROM user WHERE user_type_id IN (2, 3)`
- Per ogni verifier, invia email con template HTML
- Log: `📧 Verification request sent to {email}`

### 4. Verifier Riceve Email
- Email con design professionale
- Link al profilo: `http://localhost:8000/user/{user_id}`
- Informazioni utente complete

### 5. Verifier Approva (da implementare)
- Accede al profilo utente
- Verifica i contenuti
- Imposta `user.is_verified = True`
- (Opzionale) Invia notifica all'utente

## Configurazione Email

Per abilitare l'invio email, configurare le seguenti variabili d'ambiente:

```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your_sendgrid_api_key
EMAIL_FROM=noreply@helpy.com
```

## Note Tecniche

### Prevenzione Spam
- Email inviata **solo** se `is_verified = False`
- Controllo `was_verified_before` per evitare email duplicate
- Se l'utente era già verificato, non vengono inviate email

### Error Handling
- Cattura eccezioni SMTP e logga errori
- Continua a processare altri verifiers anche se uno fallisce
- Non blocca l'aggiornamento del profilo se l'email fallisce

### Logging
```python
logger.info(f"🔍 Profile verification criteria met for user {db_user.email}")
logger.info(f"📧 Verification request sent to {verifier.email}")
logger.warning("⚠️ No verifiers found in the system")
logger.error(f"❌ Failed to send email to {verifier.email}: {e}")
```

## Testing

### Test Character Counter
1. Vai a `/profile`
2. Digita nel campo "Descrizione"
3. Verifica che il contatore si aggiorni in tempo reale
4. Controlla che diventi verde a 200+ caratteri

### Test Email Notification
1. Crea un utente con `user_type_id = 2` (Verifier)
2. Logga con un utente normale
3. Compila tutti i campi del profilo con descrizione ≥200 caratteri
4. Salva
5. Verifica che il verifier riceva l'email

### Simulazione Senza Email Service
- Controlla i log: dovrebbero apparire messaggi `📧 Verification request sent to...`
- Se SMTP non configurato, verrà loggato un errore ma il profilo verrà salvato comunque

## Future Enhancements

1. **Admin Panel**: Pagina dedicata per verifiers con lista utenti pendenti
2. **Notifica Utente**: Email all'utente quando il profilo viene verificato
3. **Badge Verificato**: Icona ✓ accanto al nome utente verificato
4. **Dashboard Stats**: Numero di profili in attesa di verifica
5. **Rigetto Profilo**: Possibilità per verifier di rigettare con motivazione
6. **History Log**: Tracciare chi ha verificato quale profilo e quando
