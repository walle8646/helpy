"""Controlla che il JavaScript scritto dentro i template sia almeno sintatticamente sano.

Motivo: una stringa con un a capo dentro (capita patchando i template da riga
di comando, dove \\n diventa un ritorno a capo vero) e' un errore di sintassi
che il browser non perdona: l'intero blocco <script> non viene eseguito e
tutte le funzioni della pagina spariscono. E' successo sulla pagina social,
dove "Genera contenuti" rispondeva solo con
"generateDrafts is not defined" in console.
"""
import glob
import io
import os
import re

TEMPLATES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "templates")


def blocchi_script(html):
    """I blocchi <script> con del codice dentro (quelli con src= non contano)."""
    for m in re.finditer(r"<script\b([^>]*)>(.*?)</script>", html, re.S | re.I):
        if re.search(r"\bsrc\s*=", m.group(1), re.I):
            continue
        yield html[: m.start(2)].count("\n") + 1, m.group(2)


def _scorri(corpo, i, n, riga, errori, fine_su=None):
    """Scorre il codice tenendo conto di commenti, stringhe, template e regex.

    Si ferma su `fine_su`: serve per i ${...} dentro i template literal, che
    contengono codice a loro volta.
    """
    prec = ""
    while i < n:
        c = corpo[i]
        if fine_su and c == fine_su and prec != "":
            return i, riga
        if c == "\n":
            riga += 1
            i += 1
            continue
        if c in " \t\r":
            i += 1
            continue
        if corpo.startswith("//", i):
            j = corpo.find("\n", i)
            i = n if j < 0 else j
            continue
        if corpo.startswith("/*", i):
            j = corpo.find("*/", i + 2)
            if j < 0:
                return n, riga
            riga += corpo.count("\n", i, j)
            i = j + 2
            continue
        if c in "'\"":
            apertura = riga
            j = i + 1
            while j < n:
                if corpo[j] == "\\":
                    j += 2
                    continue
                if corpo[j] == "\n":
                    errori.append((apertura, corpo[i:j].strip()[:70]))
                    riga += 1
                    break
                if corpo[j] == c:
                    break
                j += 1
            i = j + 1
            prec = c
            continue
        if c == "`":
            j = i + 1
            while j < n:
                if corpo[j] == "\\":
                    j += 2
                    continue
                if corpo[j] == "\n":
                    riga += 1
                    j += 1
                    continue
                if corpo.startswith("${", j):
                    j, riga = _scorri(corpo, j + 2, n, riga, errori, "}")
                    j += 1
                    continue
                if corpo[j] == "`":
                    break
                j += 1
            i = j + 1
            prec = "`"
            continue
        if c == "/" and (prec == "" or prec in "(,=:[!&|?{};+-*~%<>^"):
            j = i + 1
            in_classe = False
            while j < n:
                if corpo[j] == "\\":
                    j += 2
                    continue
                if corpo[j] == "\n":
                    break
                if corpo[j] == "[":
                    in_classe = True
                elif corpo[j] == "]":
                    in_classe = False
                elif corpo[j] == "/" and not in_classe:
                    break
                j += 1
            i = j + 1
            prec = "/"
            continue
        prec = c
        i += 1
    return i, riga


def stringhe_aperte(percorso):
    """Righe dove una stringo '...' o "..." resta aperta a fine riga."""
    html = io.open(percorso, encoding="utf-8").read()
    errori = []
    for riga_base, corpo in blocchi_script(html):
        _scorri(corpo, 0, len(corpo), riga_base, errori)
    return errori


def test_nessuna_stringa_javascript_aperta_a_fine_riga():
    brutti = []
    for percorso in sorted(glob.glob(os.path.join(TEMPLATES, "**", "*.html"), recursive=True)):
        for riga, frammento in stringhe_aperte(percorso):
            brutti.append("%s:%s -> %s" % (os.path.relpath(percorso, TEMPLATES), riga, frammento))
    assert not brutti, (
        "Stringhe JavaScript non chiuse: il browser non esegue l'intero <script> "
        "e la pagina resta senza funzioni.\n" + "\n".join(brutti)
    )


def _tutto_il_javascript():
    """Tutto il JS del sito: i template (anche quelli inclusi) e i file statici."""
    pezzi = []
    for percorso in glob.glob(os.path.join(TEMPLATES, "**", "*.html"), recursive=True):
        html = io.open(percorso, encoding="utf-8").read()
        pezzi.extend(corpo for _, corpo in blocchi_script(html))
    statici = os.path.join(os.path.dirname(TEMPLATES), "static")
    for percorso in glob.glob(os.path.join(statici, "**", "*.js"), recursive=True):
        pezzi.append(io.open(percorso, encoding="utf-8", errors="ignore").read())
    return "\n".join(pezzi)


def test_le_funzioni_usate_negli_onclick_esistono():
    """Un onclick="pippo()" senza la funzione pippo da nessuna parte e' un bottone morto."""
    codice = _tutto_il_javascript()
    parole_chiave = {"return", "this", "if", "alert", "confirm", "typeof", "new", "void"}
    mancanti = []
    for percorso in sorted(glob.glob(os.path.join(TEMPLATES, "**", "*.html"), recursive=True)):
        for numero, riga in enumerate(io.open(percorso, encoding="utf-8"), start=1):
            if riga.lstrip().startswith("//") or riga.lstrip().startswith("*"):
                continue  # e' un commento nel JS, non un vero handler
            for m in re.finditer(r'on(?:click|change|submit|input)="([A-Za-z_$][\w$]*)\s*\(', riga):
                nome = m.group(1)
                if nome in parole_chiave:
                    continue
                definita = (
                    re.search(r"\bfunction\s+%s\b" % re.escape(nome), codice)
                    or re.search(r"\b(?:const|let|var)\s+%s\s*=" % re.escape(nome), codice)
                    or re.search(r"\bwindow\.%s\s*=" % re.escape(nome), codice)
                )
                if not definita:
                    mancanti.append("%s:%s -> %s()" % (os.path.relpath(percorso, TEMPLATES), numero, nome))
    assert not mancanti, "Handler inline senza funzione definita:\n" + "\n".join(mancanti)
