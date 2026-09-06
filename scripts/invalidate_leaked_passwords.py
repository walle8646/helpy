"""Invalida le password compromesse e avvisa gli utenti.

Contesto: fino al 2026-09-06 il repository pubblico conteneva un dump con gli
hash MD5 senza salt di tutti gli utenti registrati. MD5 senza salt si rompe
offline in minuti con una wordlist, quindi quelle password vanno considerate
note a chiunque abbia clonato il repository, e restano valide finché non
vengono cambiate — anche dopo la bonifica della storia git.

Cosa fa lo script, per ogni utente selezionato:
  1. sostituisce l'hash con un valore che non può corrispondere a nulla
     (app.utils.password.UNUSABLE_PASSWORD), così le credenziali trapelate
     smettono di funzionare;
  2. invia un'email che spiega l'accaduto e invita a usare "password
     dimenticata" per impostarne una nuova.

Chi accede con Google non viene toccato: non ha una password da invalidare.

USO — parte sempre in simulazione, non tocca niente finché non si passa --esegui:

    # 1. Vedi chi verrebbe coinvolto
    python scripts/invalidate_leaked_passwords.py

    # 2. Restringi a chi era davvero nel dump (consigliato)
    python scripts/invalidate_leaked_passwords.py --prima-di 2025-11-19

    # 3. Solo alcuni indirizzi, letti da file (uno per riga)
    python scripts/invalidate_leaked_passwords.py --file email_esposte.txt

    # 4. Esecuzione vera
    python scripts/invalidate_leaked_passwords.py --prima-di 2025-11-19 --esegui

    # ...senza mandare email (se preferisci avvisare tu)
    python scripts/invalidate_leaked_passwords.py --prima-di 2025-11-19 --esegui --niente-email
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlmodel import Session, select  # noqa: E402

from app.database import engine  # noqa: E402
from app.models import User  # noqa: E402
from app.utils.password import UNUSABLE_PASSWORD, is_legacy_hash  # noqa: E402


TESTO_EMAIL = """
<p>Ciao <strong>{nome}</strong>,</p>

<p>Per motivi di sicurezza abbiamo <strong>disattivato la password</strong> del tuo
account Ispiramy. Nessun altro dato del tuo profilo è stato modificato e le tue
consulenze sono al loro posto.</p>

<p>Per rientrare bastano pochi secondi: vai alla pagina di accesso, scegli
<strong>“Password dimenticata”</strong> e impostane una nuova.</p>

<p>Ti consigliamo di scegliere una password che non usi su altri siti. Se la
stessa password era usata altrove, cambiala anche lì.</p>

<p>Ci scusiamo per il disturbo.</p>
"""


def seleziona_utenti(session, prima_di: datetime | None, emails: list[str] | None,
                     solo_legacy: bool) -> list[User]:
    query = select(User)
    if emails:
        query = query.where(User.email.in_(emails))
    if prima_di is not None:
        query = query.where(User.created_at < prima_di)

    utenti = session.exec(query).all()

    selezionati = []
    for u in utenti:
        if u.password_md5 == UNUSABLE_PASSWORD:
            continue  # già invalidata
        if u.google_id and not is_legacy_hash(u.password_md5):
            continue  # accede con Google, non ha una password da invalidare
        if solo_legacy and not is_legacy_hash(u.password_md5):
            continue  # ha già una password bcrypt, impostata dopo la fuga
        selezionati.append(u)
    return selezionati


def avvisa(user: User) -> bool:
    from app.utils.email import send_email
    from app.utils.notification_email import _branded_email

    nome = user.nome or user.email.split("@")[0]
    html = _branded_email(
        "🔐", "Reimposta la tua password", "#43a047", "#2e7d32",
        TESTO_EMAIL.format(nome=nome),
        "Reimposta la password",
        f"{__import__('os').getenv('BASE_URL', 'https://ispiramy.com')}/reset-password",
    )
    return send_email(user.email, "Reimposta la tua password Ispiramy", html)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--esegui", action="store_true",
                    help="applica davvero le modifiche (senza, è solo una simulazione)")
    ap.add_argument("--prima-di", metavar="AAAA-MM-GG",
                    help="limita agli utenti creati prima di questa data (quelli presenti nel dump)")
    ap.add_argument("--file", metavar="PERCORSO",
                    help="file con gli indirizzi email da colpire, uno per riga")
    ap.add_argument("--niente-email", action="store_true",
                    help="invalida senza mandare l'avviso agli utenti")
    ap.add_argument("--tutti", action="store_true",
                    help="includi anche chi ha già una password bcrypt (di norma non serve)")
    args = ap.parse_args()

    prima_di = None
    if args.prima_di:
        try:
            prima_di = datetime.strptime(args.prima_di, "%Y-%m-%d")
        except ValueError:
            print(f"❌ Data non valida: {args.prima_di} (formato atteso AAAA-MM-GG)")
            return 2

    emails = None
    if args.file:
        percorso = Path(args.file)
        if not percorso.exists():
            print(f"❌ File non trovato: {percorso}")
            return 2
        emails = [r.strip().lower() for r in percorso.read_text(encoding="utf-8").splitlines() if r.strip()]
        print(f"📄 {len(emails)} indirizzi letti da {percorso}")

    with Session(engine) as session:
        utenti = seleziona_utenti(session, prima_di, emails, solo_legacy=not args.tutti)

        if not utenti:
            print("✅ Nessun utente da invalidare con questi criteri.")
            return 0

        print(f"\n{'ESECUZIONE' if args.esegui else 'SIMULAZIONE'} — {len(utenti)} utenti coinvolti:\n")
        for u in utenti:
            tipo = "MD5 legacy" if is_legacy_hash(u.password_md5) else "bcrypt"
            creato = u.created_at.strftime("%Y-%m-%d") if u.created_at else "?"
            print(f"  #{u.id:<5} {u.email:<40} {tipo:<11} creato {creato}")

        if not args.esegui:
            print("\n⚠️  Simulazione: nessuna modifica applicata.")
            print("   Aggiungi --esegui per procedere davvero.")
            return 0

        conferma = input(f"\nInvalidare la password di {len(utenti)} utenti? Scrivi 'CONFERMO': ")
        if conferma.strip() != "CONFERMO":
            print("Annullato.")
            return 1

        invalidati = 0
        for u in utenti:
            u.password_md5 = UNUSABLE_PASSWORD
            session.add(u)
            invalidati += 1
        session.commit()
        print(f"\n🔒 {invalidati} password invalidate.")

        if args.niente_email:
            print("📭 Nessuna email inviata (--niente-email).")
            return 0

        inviate = 0
        for u in utenti:
            try:
                if avvisa(u):
                    inviate += 1
            except Exception as e:  # noqa: BLE001
                print(f"   ⚠️ Email non inviata a {u.email}: {e}")
        print(f"📧 {inviate}/{len(utenti)} avvisi inviati.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
