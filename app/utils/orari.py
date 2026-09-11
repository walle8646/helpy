"""Orari: una sola convenzione per tutto quello che finisce nel database.

Le colonne datetime dei modelli sono TIMESTAMP WITHOUT TIME ZONE e contengono
**ora italiana senza fuso**, come gli orari delle prenotazioni.

Salvarci un datetime CON fuso (`datetime.now(ITALY_TZ)`) è un errore sottile:
psycopg2 lo manda a PostgreSQL come timestamptz, e PostgreSQL, per farlo
entrare in una colonna senza fuso, lo converte nel fuso della sessione. Con un
database in UTC (il default di Render) le 15:30 italiane diventano 13:30.
SQLite invece toglie semplicemente il fuso: in locale e nei test il problema
non si vede.
"""
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

ITALY_TZ = ZoneInfo("Europe/Rome")


def now_italy_naive() -> datetime:
    """Ora corrente italiana, senza fuso: il valore da salvare nel database."""
    return datetime.now(ITALY_TZ).replace(tzinfo=None)


def iso_ora_italiana(dt: Optional[datetime]) -> Optional[str]:
    """ISO 8601 con il fuso esplicito, per mandare al browser un orario salvato.

    Senza offset ("2026-09-11T15:30:00") il browser interpreta l'orario nel
    proprio fuso; con l'offset il risultato è lo stesso istante ovunque.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ITALY_TZ)
    return dt.isoformat()
