"""Genera lo sfondo virtuale della call (app/static/call-background.png).

Si lancia dalla radice del progetto:
    python scripts/genera_sfondo_call.py

Il marchio sta in basso a destra ma dentro la fascia centrale: la webcam
riprende spesso in 4:3 e l'immagine, larga 16:9, viene ritagliata ai lati.
Con il logo attaccato al bordo destro, in call non si vedeva.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

RADICE = Path(__file__).resolve().parent.parent
LOGO = RADICE / "app" / "static" / "logo-marchio.png"      # logo bianco su trasparente
USCITA = RADICE / "app" / "static" / "call-background.png"

L, A = 1280, 720
CHIARO = (244, 251, 244)
SCURO = (214, 234, 215)
VERDE_SCURO = (46, 125, 50)
VERDE_CHIARO = (102, 187, 106)
LATO_LOGO = 132
CORPO_TESTO = 58
MARGINE_DESTRO = 1080   # dentro la parte visibile anche in 4:3
CENTRO_VERTICALE = 632


def _sfumatura_diagonale() -> Image.Image:
    verticale = Image.new("RGB", (L, A))
    dv = ImageDraw.Draw(verticale)
    for y in range(A):
        q = y / (A - 1)
        dv.line([(0, y), (L, y)], fill=tuple(round(CHIARO[i] + (SCURO[i] - CHIARO[i]) * q) for i in range(3)))
    orizzontale = Image.new("RGB", (L, A))
    do = ImageDraw.Draw(orizzontale)
    for x in range(L):
        q = x / (L - 1)
        do.line([(x, 0), (x, A)], fill=tuple(round(CHIARO[i] + (SCURO[i] - CHIARO[i]) * q) for i in range(3)))
    return Image.blend(verticale, orizzontale, 0.5)


def _cerchi() -> Image.Image:
    cerchi = Image.new("RGBA", (L, A), (0, 0, 0, 0))
    dc = ImageDraw.Draw(cerchi)
    for (cx, cy, r, alfa) in [(150, 115, 110, 56), (1200, 90, 70, 60), (1150, 620, 165, 54), (90, 640, 75, 52)]:
        dc.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, alfa))
    return cerchi.filter(ImageFilter.GaussianBlur(6))


def _logo_colorato() -> Image.Image:
    """Il logo bianco ricolorato con la sfumatura del marchio."""
    bianco = Image.open(LOGO).convert("RGBA").resize((LATO_LOGO, LATO_LOGO), Image.LANCZOS)
    sfumatura = Image.new("RGBA", (LATO_LOGO, LATO_LOGO))
    ds = ImageDraw.Draw(sfumatura)
    for i in range(LATO_LOGO):
        q = i / (LATO_LOGO - 1)
        colore = tuple(round(VERDE_CHIARO[k] + (VERDE_SCURO[k] - VERDE_CHIARO[k]) * q) for k in range(3))
        ds.line([(0, i), (LATO_LOGO, i)], fill=colore + (255,))
    vuoto = Image.new("RGBA", (LATO_LOGO, LATO_LOGO), (0, 0, 0, 0))
    return Image.composite(sfumatura, vuoto, bianco.split()[3])


def _font(dimensione: int):
    for percorso in ("C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(percorso, dimensione)
        except OSError:
            continue
    return ImageFont.load_default()


def genera() -> Path:
    sfondo = Image.alpha_composite(_sfumatura_diagonale().convert("RGBA"), _cerchi())
    disegna = ImageDraw.Draw(sfondo)

    font = _font(CORPO_TESTO)
    testo = "Ispiramy"
    riquadro = disegna.textbbox((0, 0), testo, font=font)
    larghezza_testo = riquadro[2] - riquadro[0]
    altezza_testo = riquadro[3] - riquadro[1]

    x = MARGINE_DESTRO - (LATO_LOGO + 18 + larghezza_testo)
    sfondo.alpha_composite(_logo_colorato(), (x, CENTRO_VERTICALE - LATO_LOGO // 2))
    disegna.text((x + LATO_LOGO + 18, CENTRO_VERTICALE - altezza_testo // 2 - riquadro[1]),
                 testo, font=font, fill=VERDE_SCURO + (255,))

    sfondo.convert("RGB").save(USCITA, optimize=True)
    return USCITA


if __name__ == "__main__":
    print(f"Sfondo creato: {genera()}")
