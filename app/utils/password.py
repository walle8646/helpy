"""Hashing e verifica delle password.

Storicamente le password erano hashate in **MD5 semplice**, senza salt: un hash
del genere si rompe offline in pochi minuti con una wordlist, e chiunque metta
le mani sul database (o su un suo dump) ottiene le password in chiaro.

Qui si passa a **bcrypt**, con migrazione trasparente: al primo login riuscito
la password viene ri-hashata in bcrypt e l'hash MD5 sparisce. Nessun utente deve
fare nulla, e non serve una migrazione SQL perché la colonna `password_md5` è un
VARCHAR senza lunghezza fissa (il nome resta per compatibilità, ma da ora
contiene un hash bcrypt).

Uso tipico in un endpoint di login:

    ok, da_ri_hashare = verify_password(password, user.password_md5)
    if not ok:
        ...credenziali errate...
    if da_ri_hashare:
        user.password_md5 = hash_password(password)
"""
import hashlib
import hmac
import re

import bcrypt

# bcrypt lavora su al massimo 72 byte: oltre, i byte in eccesso vengono ignorati
# in silenzio. Tronchiamo esplicitamente per non dare l'illusione che una
# passphrase lunghissima sia più forte di quanto sia.
_BCRYPT_MAX_BYTES = 72

_MD5_RE = re.compile(r"^[0-9a-f]{32}$")
# Un hash bcrypt e' esattamente "$2b$" + costo a 2 cifre + "$" + 53 caratteri.
# La forma va verificata per intero prima di passarlo alla libreria: su un hash
# troncato il binding Rust non solleva un'eccezione ma va in *panic*, e
# PanicException deriva da BaseException, quindi sfugge a `except Exception`
# e farebbe fallire l'intera richiesta di login.
_BCRYPT_RE = re.compile(r"^\$2[aby]?\$\d{2}\$[./A-Za-z0-9]{53}$")
_BCRYPT_PREFIX_RE = re.compile(r"^\$2[aby]?\$")

# Valore che non può corrispondere a nessuna password: né bcrypt né MD5.
# Usato per invalidare le credenziali compromesse e obbligare al reset.
UNUSABLE_PASSWORD = "!disabilitata"


def _prepare(password: str) -> bytes:
    return (password or "").encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Genera un hash bcrypt della password."""
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def is_legacy_hash(stored: str) -> bool:
    """True se l'hash memorizzato è ancora il vecchio MD5."""
    return bool(stored) and bool(_MD5_RE.match(stored))


def verify_password(password: str, stored: str) -> tuple[bool, bool]:
    """Verifica la password contro l'hash memorizzato.

    Ritorna (valida, va_ri_hashata). `va_ri_hashata` è True quando la password
    è corretta ma l'hash è ancora nel vecchio formato MD5: il chiamante deve
    salvare `hash_password(password)` per completare la migrazione.
    """
    if not stored or stored == UNUSABLE_PASSWORD:
        return False, False

    if _BCRYPT_RE.match(stored):
        try:
            return bcrypt.checkpw(_prepare(password), stored.encode("utf-8")), False
        except BaseException:  # noqa: BLE001 — include il panic del binding Rust
            return False, False

    if _BCRYPT_PREFIX_RE.match(stored):
        # Sembra bcrypt ma non lo e': hash troncato o corrotto in scrittura.
        # Non va passato alla libreria (vedi commento su _BCRYPT_RE).
        return False, False

    if is_legacy_hash(stored):
        legacy = hashlib.md5((password or "").encode("utf-8")).hexdigest()
        # compare_digest per non perdere tempo su timing attack proprio ora
        if hmac.compare_digest(legacy, stored):
            return True, True
        return False, False

    return False, False
