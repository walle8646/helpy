"""I valori scritti dagli utenti non devono diventare HTML nelle email.

Il commento di una recensione (scritto dal cliente) finiva così com'era
nell'email mandata al consulente, e lo stesso valeva per nomi e titoli: chiunque
poteva inserire link o markup in un'email firmata Ispiramy.
"""
from app.utils.notification_email import generate_email_html

ATTACCO = '<a href="https://phishing.example">Clicca qui</a><img src=x onerror=alert(1)>'


def _dati(**extra):
    base = {
        "consultant_name": "Anna", "reviewer_name": "Mario", "rating": "5",
        "date": "10/01/2026", "comment": "ottimo", "action_url": "https://ispiramy.com/user/1",
    }
    base.update(extra)
    return base


class TestEscaping:
    def test_il_commento_della_recensione_non_diventa_html(self):
        html = generate_email_html("review_received.html", _dati(comment=ATTACCO))
        assert "<a href=\"https://phishing.example\">" not in html
        assert "<img src=x" not in html
        assert "&lt;a href=&quot;https://phishing.example&quot;&gt;" in html

    def test_anche_i_nomi_vengono_escapati(self):
        html = generate_email_html("review_received.html", _dati(reviewer_name="<b>Admin</b>"))
        assert "<b>Admin</b>" not in html
        assert "&lt;b&gt;Admin&lt;/b&gt;" in html

    def test_un_apice_non_esce_dall_attributo_href(self):
        url = 'https://ispiramy.com/x" onmouseover="alert(1)'
        html = generate_email_html("review_received.html", _dati(action_url=url))
        assert 'onmouseover="alert(1)"' not in html

    def test_la_e_commerciale_negli_url_e_corretta(self):
        html = generate_email_html("review_received.html",
                                   _dati(action_url="https://ispiramy.com/p?a=1&b=2"))
        assert 'href="https://ispiramy.com/p?a=1&amp;b=2"' in html

    def test_reason_section_resta_html(self):
        """È costruito dal codice, con il motivo già escapato al suo interno."""
        sezione = "<div class=\"motivo\"><p>Indisponibile quel giorno</p></div>"
        html = generate_email_html("booking_refused.html", {
            "client_name": "Mario", "consultant_name": "Anna", "date": "10/01/2026",
            "time": "10:00", "reason_section": sezione, "action_url": "https://ispiramy.com",
        })
        assert sezione in html

    def test_i_valori_normali_restano_leggibili(self):
        html = generate_email_html("review_received.html", _dati(comment="Molto chiaro, grazie!"))
        assert "Molto chiaro, grazie!" in html
