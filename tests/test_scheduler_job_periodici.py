"""I job periodici devono recuperare il lavoro arretrato dopo un riavvio.

APScheduler, quando un job a intervallo viene ri-registrato all'avvio, fa
ripartire il conto da zero: il prossimo giro e' fra N minuti, non subito. Su
Render ogni push e' un riavvio, quindi con deploy ravvicinati un job da 5
minuti puo' non girare mai. E' successo davvero: un post social programmato
per le 15:45 e' rimasto fermo perche' tre deploy di fila hanno rimandato il
giro.

Gli altri job periodici hanno una chiamata di recupero in fondo a
start_scheduler(); process_social_queue non puo' averla (fa chiamate di rete
e bloccherebbe l'avvio) e usa next_run_time. Questo test e' statico apposta:
il problema e' nella registrazione, non nell'esecuzione.
"""
import ast
from pathlib import Path

import pytest

SCHEDULER = Path(__file__).resolve().parent.parent / "app" / "scheduler.py"


def _chiamate_add_job():
    albero = ast.parse(SCHEDULER.read_text(encoding="utf-8-sig"))
    for nodo in ast.walk(albero):
        if not isinstance(nodo, ast.Call):
            continue
        funzione = nodo.func
        if not (isinstance(funzione, ast.Attribute) and funzione.attr == "add_job"):
            continue
        argomenti = {k.arg: k.value for k in nodo.keywords if k.arg}
        identificativo = argomenti.get("id")
        if isinstance(identificativo, ast.Constant):
            yield identificativo.value, argomenti


def _funzioni_chiamate_nel_recupero():
    """I nomi chiamati direttamente dentro start_scheduler (il blocco recovery)."""
    albero = ast.parse(SCHEDULER.read_text(encoding="utf-8-sig"))
    for nodo in ast.walk(albero):
        if isinstance(nodo, ast.FunctionDef) and nodo.name == "start_scheduler":
            return {
                n.func.id
                for n in ast.walk(nodo)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            }
    return set()


def _e_a_intervallo(argomenti):
    trigger = argomenti.get("trigger")
    return (
        isinstance(trigger, ast.Call)
        and isinstance(trigger.func, ast.Name)
        and trigger.func.id == "IntervalTrigger"
    )


def test_ogni_job_periodico_recupera_dopo_un_riavvio():
    recuperate = _funzioni_chiamate_nel_recupero()
    scoperti = []
    for identificativo, argomenti in _chiamate_add_job():
        if not _e_a_intervallo(argomenti):
            continue
        if "next_run_time" in argomenti:
            continue  # parte da solo poco dopo l'avvio
        if identificativo in recuperate:
            continue  # richiamato a mano nel blocco di recupero
        scoperti.append(identificativo)
    assert not scoperti, (
        "Job periodici che dopo un riavvio aspettano un intervallo intero "
        "senza recuperare l'arretrato: " + ", ".join(scoperti)
    )


def test_la_coda_social_parte_poco_dopo_l_avvio():
    for identificativo, argomenti in _chiamate_add_job():
        if identificativo == "process_social_queue":
            assert "next_run_time" in argomenti, (
                "process_social_queue deve partire subito dopo l'avvio: senza, "
                "un deploy ogni pochi minuti rimanda all'infinito i post programmati"
            )
            return
    pytest.fail("job process_social_queue non registrato")
