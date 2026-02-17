# 📚 API Reference — Helpy

Documentazione completa di tutte le API REST esposte dalla piattaforma Helpy.

> **Base URL**: `http://localhost:10000` (sviluppo) / `https://helpy.onrender.com` (produzione)

---

## 📋 Indice

- [Autenticazione](#-autenticazione)
- [Profilo Utente](#-profilo-utente)
- [Profilo Pubblico](#-profilo-pubblico)
- [Consulenti](#-consulenti)
- [Messaggi](#-messaggi)
- [Community](#-community)
- [Disponibilità](#-disponibilità)
- [Prenotazioni](#-prenotazioni)
- [Offerte Consulenza](#-offerte-consulenza)
- [Notifiche](#-notifiche)
- [Stripe Webhook](#-stripe-webhook)
- [API Generali](#-api-generali)

---

## 🔑 Autenticazione

L'autenticazione avviene tramite JWT salvato nella sessione. Il token è ottenuto al login e viene incluso automaticamente nei cookie di sessione.

### POST `/api/login`

Effettua il login utente.

**Request Body** (JSON):
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response** (200 OK):
```json
{
  "status": "ok",
  "redirect": "/profile"
}
```

**Errori**:
- `401` — Credenziali non valide
- `403` — Email non confermata

---

### POST `/api/register`

Registra un nuovo utente.

**Request Body** (JSON):
```json
{
  "email": "user@example.com",
  "password": "Password1!",
  "password2": "Password1!",
  "privacy": true,
  "newsletter": false
}
```

**Validazioni password**:
- Minimo 8 caratteri
- Almeno una lettera maiuscola
- Almeno un numero
- Almeno un carattere speciale

**Response** (200 OK):
```json
{
  "status": "ok",
  "message": "Controlla la tua email per il codice di conferma"
}
```

---

### POST `/api/confirm`

Conferma l'email con il codice a 6 cifre.

**Request Body** (JSON):
```json
{
  "email": "user@example.com",
  "code": "123456"
}
```

**Response** (200 OK):
```json
{
  "status": "ok",
  "redirect": "/login"
}
```

---

### POST `/api/resend-confirmation`

Invia nuovamente il codice di conferma.

**Request Body** (JSON):
```json
{
  "email": "user@example.com"
}
```

---

### POST `/api/forgot-password`

Invia email per il reset della password.

**Request Body** (JSON):
```json
{
  "email": "user@example.com"
}
```

---

### POST `/api/reset-password`

Resetta la password con il token ricevuto via email.

**Request Body** (JSON):
```json
{
  "token": "jwt_reset_token",
  "password": "NewPassword1!",
  "password2": "NewPassword1!"
}
```

---

### GET `/logout`

Effettua il logout e cancella la sessione.

**Response**: Redirect a `/`

---

## 👤 Profilo Utente

> Richiede autenticazione.

### GET `/profile`

Pagina profilo dell'utente loggato (HTML).

---

### POST `/profile/update`

Aggiorna i dati del profilo.

**Request Body** (form multipart):

| Campo | Tipo | Descrizione |
|---|---|---|
| `nome` | string | Nome |
| `cognome` | string | Cognome |
| `telefono` | string | Numero di telefono |
| `professione` | string | Professione |
| `citta` | string | Città |
| `descrizione` | string | Bio / descrizione |
| `eta` | integer | Età |
| `is_consultant` | boolean | Se è un consulente |
| `anonymous` | boolean | Profilo anonimo |
| `category_id` | integer | ID categoria principale |
| `subcategories` | string (JSON) | Array JSON di ID sottocategorie |
| `prezzo_min` | float | Prezzo minimo consulenza (€) |
| `prezzo_max` | float | Prezzo massimo consulenza (€) |
| `aree_interesse` | string | Aree di interesse |
| `profile_picture` | file | Immagine profilo (max 5MB) |

**Response**: Redirect a `/profile`

---

### POST `/profile/remove-picture`

Rimuove la foto profilo (cancella anche da S3).

**Response**: Redirect a `/profile`

---

### POST `/profile/update-password`

Cambia la password dell'utente.

**Request Body** (form):

| Campo | Tipo | Descrizione |
|---|---|---|
| `current_password` | string | Password attuale |
| `new_password` | string | Nuova password |
| `confirm_password` | string | Conferma nuova password |

---

### POST `/profile/delete-account`

Elimina l'account e tutti i dati associati.

**Request Body** (form):

| Campo | Tipo | Descrizione |
|---|---|---|
| `password` | string | Password per conferma |

---

## 🌐 Profilo Pubblico

### GET `/public-profile/{user_id}`

Pagina pubblica del profilo consulente (HTML).

---

## 🔎 Consulenti

### GET `/consultants`

Pagina di ricerca consulenti con filtri (HTML).

**Query Parameters**:

| Parametro | Tipo | Descrizione |
|---|---|---|
| `q` | string | Testo di ricerca |
| `category` | integer | ID categoria |
| `subcategory` | integer | ID sottocategoria |
| `price_min` | float | Prezzo minimo |
| `price_max` | float | Prezzo massimo |
| `city` | string | Città |
| `page` | integer | Pagina (default: 1) |
| `per_page` | integer | Risultati per pagina (default: 12) |

---

### GET `/api/subcategories/{category_id}`

Ritorna le sottocategorie di una categoria principale.

**Response** (JSON):
```json
[
  {"id": 1, "nome": "Web Design"},
  {"id": 2, "nome": "Graphic Design"}
]
```

---

## 💬 Messaggi

> Tutti gli endpoint richiedono autenticazione.

### GET `/messages`

Pagina lista conversazioni (HTML).

---

### GET `/messages/{user_id}`

Pagina chat con un utente specifico (HTML).

---

### POST `/api/messages/send`

Invia un messaggio.

**Request Body** (JSON):
```json
{
  "receiver_id": 123,
  "content": "Ciao, avrei bisogno di una consulenza"
}
```

**Response** (200 OK):
```json
{
  "status": "ok",
  "message": {
    "id": 456,
    "sender_id": 1,
    "receiver_id": 123,
    "content": "Ciao, avrei bisogno di una consulenza",
    "created_at": "2024-01-15T10:30:00"
  }
}
```

---

### GET `/api/messages/{user_id}`

Recupera i messaggi della conversazione (polling).

**Query Parameters**:

| Parametro | Tipo | Descrizione |
|---|---|---|
| `after` | integer | ID ultimo messaggio ricevuto (per aggiornamenti) |

**Response** (JSON):
```json
{
  "messages": [
    {
      "id": 457,
      "sender_id": 123,
      "receiver_id": 1,
      "content": "Certo, posso aiutarti!",
      "created_at": "2024-01-15T10:31:00",
      "is_read": false
    }
  ]
}
```

---

### POST `/api/messages/read`

Segna i messaggi come letti.

**Request Body** (JSON):
```json
{
  "conversation_with": 123
}
```

---

### GET `/api/messages/unread-count`

Conta i messaggi non letti totali.

**Response** (JSON):
```json
{
  "count": 5
}
```

---

## 🏘️ Community

> Endpoint per le domande e risposte della community.

### GET `/community`

Pagina community con lista domande (HTML).

**Query Parameters**:

| Parametro | Tipo | Descrizione |
|---|---|---|
| `category` | integer | Filtra per categoria |
| `q` | string | Testo di ricerca |
| `page` | integer | Pagina |
| `sort` | string | Ordinamento: `recent`, `popular` |

---

### POST `/api/community/ask`

Crea una nuova domanda.

**Request Body** (form):

| Campo | Tipo | Descrizione |
|---|---|---|
| `titolo` | string | Titolo della domanda |
| `descrizione` | string | Descrizione dettagliata |
| `category_id` | integer | Categoria (opzionale) |
| `is_anonymous` | boolean | Pubblica come anonimo |

**Response**: Redirect a `/community`

---

### POST `/api/community/answer/{question_id}`

Rispondi a una domanda.

**Request Body** (form):

| Campo | Tipo | Descrizione |
|---|---|---|
| `content` | string | Testo della risposta |

---

### POST `/api/community/like/{question_id}`

Metti/togli like a una domanda.

**Response** (JSON):
```json
{
  "status": "ok",
  "liked": true,
  "count": 15
}
```

---

### POST `/api/community/follow/{question_id}`

Segui/smetti di seguire una domanda.

**Response** (JSON):
```json
{
  "status": "ok",
  "following": true
}
```

---

### POST `/api/community/contact/{question_id}`

Contatta l'autore di una domanda (avvia chat).

> Solo per consulenti.

---

### POST `/api/community/validate/{question_id}`

Valida o rifiuta una domanda.

> Solo per admin/verifier.

**Request Body** (JSON):
```json
{
  "action": "approve"
}
```

---

## 📅 Disponibilità

> Gestione fasce orarie del consulente. Richiede autenticazione.

### GET `/availability`

Pagina gestione disponibilità (HTML). Mostra calendario settimanale.

---

### POST `/api/availability/add`

Aggiunge un blocco di disponibilità.

**Request Body** (JSON):
```json
{
  "date": "2024-01-20",
  "start_time": "09:00",
  "end_time": "12:00"
}
```

**Response** (JSON):
```json
{
  "status": "ok",
  "block": {
    "id": 1,
    "date": "2024-01-20",
    "start_time": "09:00",
    "end_time": "12:00"
  }
}
```

---

### DELETE `/api/availability/{block_id}`

Rimuove un blocco di disponibilità.

**Response** (JSON):
```json
{
  "status": "ok"
}
```

---

### GET `/api/availability/{user_id}`

Ritorna le disponibilità di un consulente (per la pagina di prenotazione).

**Query Parameters**:

| Parametro | Tipo | Descrizione |
|---|---|---|
| `date` | string | Data specifica (YYYY-MM-DD) |

**Response** (JSON):
```json
{
  "blocks": [
    {
      "id": 1,
      "date": "2024-01-20",
      "start_time": "09:00",
      "end_time": "12:00"
    }
  ]
}
```

---

## 📞 Prenotazioni

> Sistema di prenotazione e video call.

### GET `/book/{consultant_id}`

Pagina di prenotazione con un consulente (HTML).

---

### GET `/api/booking/available-slots/{consultant_id}`

Calcola gli slot disponibili per una data.

**Query Parameters**:

| Parametro | Tipo | Descrizione |
|---|---|---|
| `date` | string | Data (YYYY-MM-DD) |
| `duration` | integer | Durata in minuti (30/60/90/120) |

**Response** (JSON):
```json
{
  "slots": [
    {"start": "09:00", "end": "09:30"},
    {"start": "09:30", "end": "10:00"},
    {"start": "10:00", "end": "10:30"}
  ]
}
```

---

### POST `/api/booking/create`

Crea una prenotazione (redirect a Stripe Checkout).

**Request Body** (JSON):
```json
{
  "consultant_id": 123,
  "date": "2024-01-20",
  "start_time": "09:00",
  "end_time": "10:00",
  "duration": 60,
  "price": 50.00,
  "topic": "Consulenza branding"
}
```

**Response** (JSON):
```json
{
  "status": "ok",
  "checkout_url": "https://checkout.stripe.com/..."
}
```

---

### GET `/booking/success`

Pagina di conferma prenotazione avvenuta (HTML).

---

### GET `/booking/cancel`

Pagina di cancellazione prenotazione (HTML).

---

### GET `/bookings`

Lista prenotazioni dell'utente (HTML).

---

### POST `/api/booking/{id}/join`

Unisciti alla video call.

**Response** (JSON):
```json
{
  "status": "ok",
  "both_joined": true,
  "recording_status": "ready"
}
```

---

### GET `/api/booking/{id}/agora-token`

Genera token Agora RTC per la video call.

**Response** (JSON):
```json
{
  "token": "007eJx...",
  "channel": "booking_123",
  "uid": 456,
  "app_id": "abc123..."
}
```

---

### POST `/api/booking/{id}/recording/start-now`

Avvia la registrazione cloud.

**Response** (JSON):
```json
{
  "status": "ok",
  "recording_status": "recording"
}
```

---

### POST `/api/booking/{id}/recording/stop`

Ferma la registrazione cloud.

**Response** (JSON):
```json
{
  "status": "ok",
  "recording_status": "stopped",
  "recording_url": "https://s3.amazonaws.com/..."
}
```

---

### GET `/api/booking/{id}/call-status`

Stato attuale della chiamata (polling).

**Response** (JSON):
```json
{
  "status": "ok",
  "call_started_at": "2024-01-20T09:00:00",
  "duration_minutes": 60,
  "elapsed_minutes": 15,
  "remaining_minutes": 45,
  "recording_status": "recording",
  "is_screen_sharing": false,
  "both_joined": true
}
```

---

### POST `/api/booking/{id}/screen-share/start`

Segnala l'inizio della condivisione schermo.

---

### POST `/api/booking/{id}/screen-share/stop`

Segnala la fine della condivisione schermo.

---

### POST `/api/booking/{id}/call-message`

Invia un messaggio nella chat in-call.

**Request Body** (form multipart):

| Campo | Tipo | Descrizione |
|---|---|---|
| `content` | string | Testo del messaggio |
| `attachment` | file | Allegato (opzionale, max 10MB) |

---

### GET `/api/booking/{id}/call-messages`

Recupera i messaggi della chat in-call.

**Query Parameters**:

| Parametro | Tipo | Descrizione |
|---|---|---|
| `after` | integer | ID ultimo messaggio ricevuto |

---

### POST `/api/booking/{id}/refuse`

Rifiuta una prenotazione e avvia il rimborso Stripe.

> Solo per il consulente.

**Response** (JSON):
```json
{
  "status": "ok",
  "message": "Prenotazione rifiutata e rimborso avviato"
}
```

---

## 💼 Offerte Consulenza

> Il consulente può creare offerte personalizzate da inviare ai clienti.

### GET `/consulenza/crea/{client_id}`

Pagina creazione offerta (HTML).

---

### POST `/consulenza/crea/{client_id}`

Crea una nuova offerta.

**Request Body** (form):

| Campo | Tipo | Descrizione |
|---|---|---|
| `price` | float | Prezzo proposto (€) |
| `duration` | integer | Durata (minuti) |
| `message` | string | Messaggio personalizzato |
| `description` | string | Descrizione della consulenza |

---

### GET `/consulenza/prenota/{offer_id}`

Pagina prenotazione basata su offerta (HTML).

---

### POST `/consulenza/prenota/{offer_id}/confirm`

Conferma prenotazione da offerta → redirect a Stripe Checkout.

**Request Body** (JSON):
```json
{
  "date": "2024-01-25",
  "start_time": "14:00"
}
```

---

## 🔔 Notifiche

### GET `/notifications`

Pagina lista notifiche (HTML).

---

### GET `/api/notifications`

Recupera notifiche in formato JSON.

**Response** (JSON):
```json
{
  "notifications": [
    {
      "id": 1,
      "type": "booking_confirmed",
      "title": "Prenotazione confermata",
      "message": "La tua prenotazione è stata confermata",
      "is_read": false,
      "created_at": "2024-01-15T10:30:00",
      "link": "/bookings"
    }
  ],
  "unread_count": 3
}
```

---

### POST `/api/notifications/{id}/read`

Segna una notifica come letta.

---

### POST `/api/notifications/read-all`

Segna tutte le notifiche come lette.

---

### GET `/api/notifications/unread-count`

Conta le notifiche non lette.

**Response** (JSON):
```json
{
  "count": 3
}
```

---

## 💳 Stripe Webhook

### POST `/webhook/stripe`

Endpoint per la ricezione degli eventi Stripe.

> Questo endpoint è chiamato direttamente da Stripe e NON richiede autenticazione utente. Verifica la firma del webhook.

**Header richiesto**:
- `Stripe-Signature` — Firma dell'evento

**Eventi gestiti**:

| Evento | Azione |
|---|---|
| `checkout.session.completed` | Crea booking, invia notifica, schedula promemoria |

---

## 🛠️ API Generali

### GET `/`

Homepage (HTML).

---

### GET `/api/categories`

Lista tutte le categorie.

**Response** (JSON):
```json
[
  {
    "id": 1,
    "nome": "Tecnologia",
    "is_principal": true,
    "subcategories": [
      {"id": 10, "nome": "Web Development"},
      {"id": 11, "nome": "Mobile Development"}
    ]
  }
]
```

---

### GET `/health`

Health check endpoint.

**Response** (JSON):
```json
{
  "status": "ok"
}
```

---

## ⚠️ Codici di Errore Comuni

| Codice | Significato |
|---|---|
| `200` | Successo |
| `400` | Richiesta non valida (parametri mancanti o errati) |
| `401` | Non autenticato |
| `403` | Non autorizzato (permessi insufficienti) |
| `404` | Risorsa non trovata |
| `422` | Errore di validazione (Unprocessable Entity) |
| `500` | Errore interno del server |

### Formato Errore Standard

```json
{
  "detail": "Messaggio di errore descrittivo"
}
```

Oppure per le risposte AJAX:

```json
{
  "status": "error",
  "message": "Messaggio di errore descrittivo"
}
```
