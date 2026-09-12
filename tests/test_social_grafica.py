"""Generazione della grafica dei draft social.

Il carosello era previsto solo per Instagram: su Facebook il bottone
"Genera grafica" non c'era proprio, e un post Facebook senza immagine passa
molto meno. Fuori da Instagram serve una sola immagine, non un carosello, e
il testo da metterci sopra va recuperato: il generatore di contenuti salva
hook e slide solo sulla riga Instagram.
"""
import json
import secrets

import pytest
from sqlmodel import Session, select

from app.database import engine
from app.models import SocialDraft
from app.social import image_generator


@pytest.fixture
def pulizia():
    creati = []
    yield creati
    with Session(engine) as s:
        for draft_id in creati:
            d = s.get(SocialDraft, draft_id)
            if d:
                s.delete(d)
        s.commit()


def _draft(pulizia, platform, caption="Testo del post.", extra=None, titolo=None, domanda=None, stato="draft"):
    with Session(engine) as s:
        d = SocialDraft(
            platform=platform,
            caption=caption,
            extra_content=json.dumps(extra, ensure_ascii=False) if extra else None,
            source_title=titolo,
            source_question_id=domanda,
            status=stato,
        )
        s.add(d)
        s.commit()
        s.refresh(d)
        pulizia.append(d.id)
        return d.id


def _hook(draft_id):
    with Session(engine) as s:
        return image_generator._hook_del_draft(s, s.get(SocialDraft, draft_id))


def test_il_facebook_riusa_l_hook_del_fratello_instagram(pulizia):
    domanda = secrets.randbelow(10**6) + 10**6
    _draft(pulizia, "instagram", extra={"hook": "Tre errori nel colloquio", "carousel_slides": ["a", "b"]},
           domanda=domanda)
    fb = _draft(pulizia, "facebook", caption="Post lungo per la pagina.", domanda=domanda)
    assert _hook(fb) == "Tre errori nel colloquio"


def test_senza_fratello_usa_il_titolo_della_domanda(pulizia):
    fb = _draft(pulizia, "facebook", titolo="Come trovare lavoro a Milano")
    assert _hook(fb) == "Come trovare lavoro a Milano"


def test_ultima_spiaggia_la_prima_frase_della_caption(pulizia):
    fb = _draft(pulizia, "facebook", caption="Cambiare lavoro spaventa. Ma si può fare. #lavoro #carriera")
    assert _hook(fb) == "Cambiare lavoro spaventa."


def test_instagram_preferisce_il_proprio_hook(pulizia):
    domanda = secrets.randbelow(10**6) + 10**6
    _draft(pulizia, "facebook", caption="Altro.", domanda=domanda)
    ig = _draft(pulizia, "instagram", extra={"hook": "Il suo hook", "carousel_slides": ["x"]},
                titolo="Titolo diverso", domanda=domanda)
    assert _hook(ig) == "Il suo hook"


def test_un_draft_pubblicato_non_si_rigenera(pulizia):
    fb = _draft(pulizia, "facebook", titolo="Un titolo", stato="published")
    esito = image_generator.generate_image_for_draft(fb, use_ai_cover=False)
    assert esito["ok"] is False
    assert "pubblicato" in esito["message"]


def test_facebook_genera_una_sola_immagine(monkeypatch, pulizia):
    """Una immagine sola, senza "Scorri": non c'è nessuna seconda slide."""
    caricate = []
    monkeypatch.setattr(image_generator, "_upload_png",
                        lambda img, key: caricate.append((img, key)) or f"https://esempio/{key}")

    fb = _draft(pulizia, "facebook", titolo="Come chiedere un aumento")
    esito = image_generator.generate_media_for_draft(fb, use_ai_cover=False)

    assert esito["ok"] is True, esito["message"]
    assert len(caricate) == 1
    immagine, chiave = caricate[0]
    assert immagine.size == (image_generator.W, image_generator.H)
    assert chiave.endswith("-post.png")
    with Session(engine) as s:
        assert "\n" not in (s.get(SocialDraft, fb).media_urls or "")


def test_instagram_passa_dal_carosello(monkeypatch, pulizia):
    chiamate = []
    monkeypatch.setattr(image_generator, "generate_carousel_for_draft",
                        lambda draft_id, use_ai_cover=True: chiamate.append(draft_id) or {"ok": True, "message": "ok"})
    ig = _draft(pulizia, "instagram", extra={"hook": "h", "carousel_slides": ["a", "b"]})
    image_generator.generate_media_for_draft(ig, use_ai_cover=False)
    assert chiamate == [ig]


def test_la_coda_ignora_i_draft_non_approvati(monkeypatch, pulizia):
    """Una data su un draft non approvato non pubblica niente: va detto nella pagina."""
    from datetime import datetime, timedelta
    from app.social import publisher

    pubblicati = []
    monkeypatch.setattr(publisher, "publish_draft",
                        lambda draft_id: pubblicati.append(draft_id) or {"ok": True})
    monkeypatch.setattr(publisher, "check_publishing_results", lambda: None)

    ieri = datetime.now() - timedelta(days=1)
    fermo = _draft(pulizia, "facebook", titolo="Non approvato", stato="draft")
    pronto = _draft(pulizia, "facebook", titolo="Approvato", stato="approved")
    with Session(engine) as s:
        for draft_id in (fermo, pronto):
            d = s.get(SocialDraft, draft_id)
            d.scheduled_at = ieri
            s.add(d)
        s.commit()

    publisher.process_social_queue()
    assert pronto in pubblicati
    assert fermo not in pubblicati

    import io
    import os
    percorso = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "app", "templates", "admin", "social.html")
    html = io.open(percorso, encoding="utf-8").read()
    assert "non è approvato" in html, "manca l'avviso per i draft programmati ma non approvati"


def test_il_bottone_genera_grafica_c_e_anche_per_facebook():
    """La regola sta nel template: senza il bottone la funzione non serve a nulla."""
    import io
    import os
    percorso = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "app", "templates", "admin", "social.html")
    html = io.open(percorso, encoding="utf-8").read()
    riga = [r for r in html.splitlines() if "generateMedia(" in r and "{% if" not in r]
    condizione = [r for r in html.splitlines() if "genmedia" in r or "generateMedia(" in r]
    assert condizione, "bottone Genera grafica sparito dal template"
    blocco = html[max(0, html.find("generateMedia({{ d.id }})") - 300):html.find("generateMedia({{ d.id }})")]
    assert "facebook" in blocco, "il bottone Genera grafica e' ancora solo per Instagram"
    assert riga, "il bottone deve restare un onclick semplice"
