"""Nessuna credenziale vera nei file di documentazione.

Il repository e' pubblico. In rules/AGORA_RECORDING_SETUP.md erano finiti
l'App ID e soprattutto l'**App Certificate** di Agora: con quei due valori
chiunque puo' generare un token valido ed entrare in un canale, e i canali
si chiamano "booking_<id>", quindi sono indovinabili. Il guaio non e' il
consumo di minuti, e' che un estraneo puo' entrare in una videoconsulenza.

Questo test guarda solo i documenti: le chiavi vere stanno nelle variabili
d'ambiente, negli esempi ci vanno i segnaposto.
"""
import re
from pathlib import Path

PROGETTO = Path(__file__).resolve().parent.parent

# Variabili il cui valore e' un segreto (non basta leggerlo per sbaglio: con
# questi si firma, si paga o si entra).
VARIABILI_SEGRETE = (
    "AGORA_APP_CERTIFICATE",
    "AGORA_CUSTOMER_SECRET",
    "AWS_SECRET_ACCESS_KEY",
    "OPENAI_API_KEY",
    "STRIPE_SECRET_KEY",
    "POSTFORME_API_KEY",
    "RESEND_API_KEY",
    "PAYPAL_CLIENT_SECRET",
    "SECRET_KEY",
)

# Un valore e' un segnaposto se contiene una di queste parti.
SEGNAPOSTO = ("x" * 4, "your", "il_tuo", "tuo_", "<", "...", "abc", "changeme",
              "placeholder", "esempio", "example", "inserisci", "qui")


def _documenti():
    for percorso in PROGETTO.rglob("*.md"):
        if ".git" in percorso.parts or "node_modules" in percorso.parts:
            continue
        yield percorso


def _sembra_vero(valore: str) -> bool:
    valore = valore.strip().strip("\"'")
    if len(valore) < 16:
        return False
    minuscolo = valore.lower()
    if any(s in minuscolo for s in SEGNAPOSTO):
        return False
    # Una credenziale vera e' densa: niente spazi, quasi tutto alfanumerico
    return " " not in valore and bool(re.fullmatch(r"[A-Za-z0-9_\-./+=]{16,}", valore))


def test_nessuna_credenziale_vera_nei_markdown():
    trovati = []
    modello = re.compile(r"^\s*(?:#\s*)?(%s)\s*[:=]\s*(\S+)" % "|".join(VARIABILI_SEGRETE))
    for percorso in _documenti():
        for numero, riga in enumerate(percorso.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            trovato = modello.match(riga)
            if trovato and _sembra_vero(trovato.group(2)):
                trovati.append("%s:%s -> %s" % (percorso.relative_to(PROGETTO), numero, trovato.group(1)))
    assert not trovati, (
        "Credenziali vere in documenti di un repository pubblico "
        "(vanno sostituite con segnaposto E ruotate, perche' restano nella "
        "cronologia git):\n" + "\n".join(trovati)
    )
