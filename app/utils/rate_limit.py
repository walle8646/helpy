"""Rate limiting in memoria per gli endpoint sensibili.

Serve a rendere impraticabili gli attacchi a forza bruta: login, richiesta di
reset password e verifica del codice a 6 cifre erano tutti senza alcun limite,
quindi un codice numerico (un milione di combinazioni) era enumerabile.

Implementazione volutamente semplice: finestra scorrevole tenuta in un dict di
processo. Regge il carico attuale (un solo worker) e non aggiunge dipendenze.
Con più processi o più istanze va sostituita con un contatore su Redis: il
limite diventerebbe per-processo invece che globale.
"""
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Tuple

from fastapi import HTTPException, Request

from app.logger_config import logger

# chiave -> timestamp dei tentativi nella finestra
_hits: Dict[str, Deque[float]] = defaultdict(deque)

# Ogni tanto ripuliamo le chiavi ormai scadute, per non far crescere il dict
_last_cleanup = 0.0
_CLEANUP_EVERY = 300  # secondi


def client_ip(request: Request) -> str:
    """IP del chiamante, tenendo conto del proxy di Render.

    Si usa il primo elemento di X-Forwarded-For (il client originale); dietro un
    proxy `request.client.host` sarebbe l'IP del proxy, uguale per tutti, e il
    limite finirebbe per bloccare l'intera piattaforma insieme.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "sconosciuto"


def _cleanup(now: float, window: int) -> None:
    global _last_cleanup
    if now - _last_cleanup < _CLEANUP_EVERY:
        return
    _last_cleanup = now
    for key in list(_hits.keys()):
        serie = _hits[key]
        while serie and now - serie[0] > window:
            serie.popleft()
        if not serie:
            del _hits[key]


def check_rate_limit(
    request: Request,
    scope: str,
    limit: int,
    window_seconds: int,
    extra_key: str = "",
) -> Tuple[bool, int]:
    """Registra un tentativo e dice se il limite è stato superato.

    Ritorna (consentito, secondi_di_attesa). `extra_key` permette di contare
    anche per email oltre che per IP, così un attacco distribuito su piu' IP
    contro un singolo account viene comunque frenato.
    """
    now = time.time()
    _cleanup(now, window_seconds)

    key = f"{scope}:{client_ip(request)}:{extra_key.lower().strip()}"
    serie = _hits[key]

    while serie and now - serie[0] > window_seconds:
        serie.popleft()

    if len(serie) >= limit:
        attesa = int(window_seconds - (now - serie[0])) + 1
        return False, max(attesa, 1)

    serie.append(now)
    return True, 0


class RateLimitExceeded(HTTPException):
    """429 con il messaggio anche nel campo `error`.

    FastAPI serializza HTTPException come {"detail": ...}, ma le pagine del sito
    (login, registrazione, reset, chat) leggono `data.error`: chi veniva
    bloccato vedeva "Codice non valido" o "Errore durante il login" invece di
    "Troppi tentativi, riprova fra N secondi". L'handler in main.py risponde
    con entrambi i campi.
    """


def enforce_rate_limit(
    request: Request,
    scope: str,
    limit: int,
    window_seconds: int,
    extra_key: str = "",
    message: str = "Troppi tentativi. Riprova fra {attesa} secondi.",
) -> None:
    """Come check_rate_limit, ma solleva direttamente un 429."""
    consentito, attesa = check_rate_limit(request, scope, limit, window_seconds, extra_key)
    if not consentito:
        logger.warning(f"⛔ Rate limit '{scope}' superato da {client_ip(request)}")
        raise RateLimitExceeded(
            status_code=429,
            detail=message.format(attesa=attesa),
            headers={"Retry-After": str(attesa)},
        )


def clear_attempts(request: Request, scope: str, extra_key: str = "") -> None:
    """Azzera i tentativi di una singola chiave.

    Da chiamare dopo un'operazione riuscita: chi sbaglia la password qualche
    volta e poi entra non deve restare a un passo dal blocco.
    """
    _hits.pop(f"{scope}:{client_ip(request)}:{extra_key.lower().strip()}", None)


def reset_rate_limit(scope: str = "") -> None:
    """Azzera i contatori. Usata dai test e dopo un login riuscito."""
    if not scope:
        _hits.clear()
        return
    for key in list(_hits.keys()):
        if key.startswith(f"{scope}:"):
            del _hits[key]
