"""Instagram accetta solo JPEG, e lo dice male.

Il carosello del draft 8 e' stato rifiutato con "Request failed with status
code 400" e nient'altro: le slide erano PNG. Due conseguenze, tutte e due
coperte qui — la grafica si genera in JPEG, e un media con un'estensione che
Instagram non accetta viene fermato prima dell'invio, con scritto cosa fare.
"""
import io
import secrets

import pytest
from PIL import Image
from sqlmodel import Session, select

from app.database import engine
from app.models import SocialDraft
from app.social import image_generator, publisher


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


def _draft(pulizia, platform="instagram", media=None, stato="approved"):
    with Session(engine) as s:
        d = SocialDraft(
            platform=platform,
            caption="Caption di prova",
            media_urls="\n".join(media) if media else None,
            status=stato,
        )
        s.add(d)
        s.commit()
        s.refresh(d)
        pulizia.append(d.id)
        return d.id


def test_le_slide_vengono_caricate_in_jpeg(monkeypatch):
    """Il PNG e' proprio il motivo del 400: quello che parte deve essere JPEG."""
    caricati = {}

    class _FintoS3:
        def put_object(self, **kwargs):
            caricati.update(kwargs)

    monkeypatch.setattr(image_generator.boto3, "client", lambda *a, **k: _FintoS3())
    immagine = Image.new("RGB", (1080, 1350), (255, 255, 255))
    url = image_generator._upload_immagine(immagine, "social/test/slide-0.jpg")

    assert caricati["ContentType"] == "image/jpeg"
    assert Image.open(io.BytesIO(caricati["Body"])).format == "JPEG"
    assert url.endswith("slide-0.jpg")


def test_instagram_non_parte_con_immagini_png(pulizia):
    draft_id = _draft(pulizia, media=[
        "https://ispiramy-images.s3.eu-north-1.amazonaws.com/social/draft-8/x-slide-0.png",
        "https://ispiramy-images.s3.eu-north-1.amazonaws.com/social/draft-8/x-slide-1.png",
    ])
    esito = publisher.publish_draft(draft_id)
    assert esito["ok"] is False
    assert "JPEG" in esito["message"]
    assert "slide-0.png" in esito["message"]


def test_le_jpeg_passano_il_controllo():
    media = ["https://esempio/a.jpg", "https://esempio/b.jpeg", "https://esempio/c.JPG"]
    assert publisher._formati_non_accettati("instagram", media) == []


def test_il_controllo_vale_solo_per_instagram():
    """Facebook e LinkedIn i PNG li accettano: non vanno bloccati."""
    media = ["https://esempio/a.png"]
    assert publisher._formati_non_accettati("facebook", media) == []
    assert publisher._formati_non_accettati("linkedin", media) == []
    assert publisher._formati_non_accettati("instagram", media) == ["a.png"]


def test_un_query_string_non_inganna_il_controllo():
    media = ["https://esempio/a.png?v=123"]
    assert publisher._formati_non_accettati("instagram", media) == ["a.png"]


def test_l_errore_opaco_si_porta_dietro_il_resto_del_risultato():
    """"Request failed with status code 400" da solo non permette di correggere niente."""
    testo = publisher._testo_errore({
        "error": "Request failed with status code 400",
        "platform": "instagram",
        "platform_message": "Only JPEG images are supported",
        "vuoto": None,
    })
    assert "status code 400" in testo
    assert "Only JPEG images are supported" in testo
    assert "vuoto" not in testo


def test_un_errore_gia_dettagliato_resta_com_e():
    dettagliato = "x" * 250
    testo = publisher._testo_errore({"error": dettagliato, "platform": "instagram"})
    assert testo == dettagliato
