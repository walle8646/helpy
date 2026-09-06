# Bonifica dei dati personali esposti nel repository

## Cos'è successo

Il repository `walle8646/ispiramy` è **pubblico** e fino al commit `8d2f9e1`
(2026-09-06) conteneva:

| File | Contenuto |
|---|---|
| `sql_update/backup_20251119.db.sql` | dump SQLite in chiaro: **70 indirizzi email** di utenti reali con i relativi **hash password MD5 senza salt** |
| `sql_update/dump-helpy-202511092202.sql` | dump `pg_dump` del database di produzione (formato binario) |
| `sql_update/dump-helpy-202511212246.sql` | idem, versione più recente |

MD5 senza salt non è un meccanismo di protezione: con una wordlist comune si
recuperano le password in chiaro in pochi minuti su un portatile. Vanno quindi
considerate **note** a chiunque abbia clonato il repository.

Il commit `8d2f9e1` ha tolto quei file da `HEAD`, ma **restano raggiungibili nei
commit precedenti**: chi conosce l'hash del commit li scarica ancora.

### Circostanze attenuanti

- Il repository ha **0 fork e 0 stelle**: non risulta clonato da terzi.
- I dump compaiono in **2 commit ciascuno**, la storia è di 124 commit: la
  riscrittura è rapida e a basso rischio.

Restano comunque due cose da fare, in quest'ordine.

---

## Passo 1 — Riscrivere la storia

Serve `git-filter-repo` (non è incluso in git):

```bash
pip install git-filter-repo
```

Lavora su un clone fresco, non sulla copia di lavoro:

```bash
git clone --mirror https://github.com/walle8646/ispiramy.git ispiramy-bonifica.git
```

Rimuovi i file da tutta la storia, su tutti i rami:

```bash
cd ispiramy-bonifica.git && git filter-repo --invert-paths --path sql_update/backup_20251119.db.sql --path sql_update/dump-helpy-202511092202.sql --path sql_update/dump-helpy-202511212246.sql --path stripe.exe --path docker_logs.txt --path docker_logs2.txt
```

Verifica che non ne resti traccia (l'output deve essere vuoto):

```bash
git log --all --oneline -- sql_update/backup_20251119.db.sql sql_update/dump-helpy-202511092202.sql sql_update/dump-helpy-202511212246.sql
```

`filter-repo` rimuove di proposito il remote, per non spingere per sbaglio.
Rimettilo e forza la scrittura:

```bash
git remote add origin https://github.com/walle8646/ispiramy.git && git push --force --all && git push --force --tags
```

> ⚠️ Da qui in poi **tutti gli hash dei commit cambiano**. Ogni copia locale
> esistente va ri-clonata: un `git pull` su un clone vecchio reintrodurrebbe la
> vecchia storia. Se lavori da più macchine, ri-clona ovunque prima di
> continuare a lavorare.

### Far sparire i commit anche dalla cache di GitHub

I vecchi commit restano accessibili su GitHub per un po' anche dopo il force
push. Per chiuderli davvero, apri un ticket al supporto GitHub
(https://support.github.com/contact) chiedendo la **garbage collection dei
commit non più referenziati** e indicando gli hash dei commit rimossi.

La strada più rapida e definitiva, se il progetto lo consente, è rendere il
repository **privato**: gli oggetti orfani cessano immediatamente di essere
raggiungibili senza autenticazione.

---

## Passo 2 — Invalidare le password trapelate

La bonifica della storia non annulla le password già lette. Vanno disattivate,
obbligando gli utenti a impostarne una nuova.

Lo script è in `scripts/invalidate_leaked_passwords.py` e **parte sempre in
simulazione**: non modifica nulla finché non si passa `--esegui`.

```bash
python scripts/invalidate_leaked_passwords.py --prima-di 2025-11-19
```

Il filtro `--prima-di` limita l'intervento a chi era effettivamente nel dump.
Chi si è registrato dopo, e chi accede con Google, non viene toccato.

Quando l'elenco ti convince:

```bash
python scripts/invalidate_leaked_passwords.py --prima-di 2025-11-19 --esegui
```

Lo script chiede una conferma esplicita, sostituisce l'hash con un valore che
non può corrispondere a nessuna password e manda a ciascun utente un'email che
spiega come reimpostarla. Con `--niente-email` invalida soltanto, se preferisci
avvisare tu.

---

## Cosa è già stato fatto

- I file sono usciti da `HEAD` (commit `8d2f9e1`) e `.gitignore` impedisce che
  rientrino: `sql_update/backup_*.sql`, `sql_update/dump-*.sql`, `prod_dump.sql`,
  `*.dump`.
- Le password nuove usano **bcrypt** (`app/utils/password.py`); quelle vecchie
  vengono convertite automaticamente al primo login riuscito. Un dump futuro non
  esporrebbe più password attaccabili con una wordlist.
- Login, registrazione, verifica email e reset password hanno un **rate limit**
  (`app/utils/rate_limit.py`): il codice a 6 cifre non è più enumerabile.
- La richiesta di reset non rivela più se un indirizzo è registrato.

## Obblighi normativi

Il dump conteneva dati personali di persone fisiche in un contesto accessibile
al pubblico. Valuta con chi segue gli aspetti legali se ricorre l'obbligo di
notifica al Garante privacy entro 72 ore dalla presa di conoscenza (art. 33
GDPR) e di comunicazione agli interessati (art. 34). Questo documento non è un
parere legale.
