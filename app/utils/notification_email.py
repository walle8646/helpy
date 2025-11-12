"""
Utility per l'invio di email notifiche usando SendGrid.

Gestisce l'invio di email basate su template HTML configurabili.
"""
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from app.logger_config import logger
from typing import Dict, Optional


def send_notification_email(
    to_email: str,
    to_name: str,
    subject: str,
    template_name: str,
    template_data: Dict[str, str]
) -> bool:
    """
    Invia un'email di notifica usando SendGrid.
    
    Args:
        to_email: Email destinatario
        to_name: Nome destinatario
        subject: Oggetto email
        template_name: Nome del template (es: 'booking_confirmed.html')
        template_data: Dizionario con variabili per il template
            es: {'client_name': 'Mario', 'date': '15/11/2025', 'time': '14:00'}
    
    Returns:
        bool: True se inviata con successo, False altrimenti
    """
    try:
        # Verifica che SendGrid sia configurato
        # Usa SMTP_PASSWORD che contiene la chiave API SendGrid
        sendgrid_api_key = os.getenv('SMTP_PASSWORD')
        from_email = os.getenv('FROM_EMAIL', 'noreply@helpy.com')
        
        if not sendgrid_api_key:
            logger.warning("SendGrid API key (SMTP_PASSWORD) non configurata, skip invio email")
            return False
        
        # Genera l'HTML del template
        html_content = generate_email_html(template_name, template_data)
        
        if not html_content:
            logger.error(f"Template {template_name} non trovato o errore generazione")
            return False
        
        # Crea il messaggio
        message = Mail(
            from_email=Email(from_email, "Helpy"),
            to_emails=To(to_email, to_name),
            subject=subject,
            html_content=Content("text/html", html_content)
        )
        
        # Invia tramite SendGrid
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        
        if response.status_code in [200, 201, 202]:
            logger.info(f"✅ Email notifica inviata a {to_email}: {subject}")
            return True
        else:
            logger.error(f"❌ Errore invio email a {to_email}: status {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Errore nell'invio email notifica: {e}")
        return False


def generate_email_html(template_name: str, data: Dict[str, str]) -> Optional[str]:
    """
    Genera l'HTML dell'email sostituendo le variabili nel template.
    
    Args:
        template_name: Nome del template (es: 'booking_confirmed.html')
        data: Dizionario con le variabili da sostituire
    
    Returns:
        str: HTML generato, None se errore
    """
    try:
        # I template email sono semplici HTML con placeholder {variable}
        templates = {
            'booking_confirmed.html': """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📅 Nuova Prenotazione!</h1>
        </div>
        <div class="content">
            <p>Ciao <strong>{consultant_name}</strong>,</p>
            <p>Hai ricevuto una nuova prenotazione da <strong>{client_name}</strong>!</p>
            
            <div class="details">
                <p><strong>📅 Data:</strong> {date}</p>
                <p><strong>🕐 Orario:</strong> {time}</p>
                <p><strong>⏱️ Durata:</strong> {duration} minuti</p>
            </div>
            
            <p>Puoi visualizzare i dettagli della prenotazione e prepararti per la consulenza.</p>
            
            <a href="{action_url}" class="button">Visualizza Prenotazione</a>
            
            <p style="margin-top: 30px; font-size: 14px; color: #666;">
                Ti consigliamo di prepararti in anticipo e di essere puntuale per offrire la migliore esperienza al tuo cliente.
            </p>
        </div>
        <div class="footer">
            <p>Questa è un'email automatica da Helpy. Non rispondere a questo messaggio.</p>
        </div>
    </div>
</body>
</html>
""",
            'reminder_1h.html': """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #fff9e6; padding: 30px; border-radius: 0 0 10px 10px; }}
        .button {{ display: inline-block; background: #f39c12; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f39c12; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔔 Promemoria Consulenza</h1>
        </div>
        <div class="content">
            <p>Ciao <strong>{user_name}</strong>,</p>
            <p>La tua consulenza con <strong>{other_user_name}</strong> inizia tra <strong>1 ora</strong>!</p>
            
            <div class="details">
                <p><strong>📅 Data:</strong> {date}</p>
                <p><strong>🕐 Orario inizio:</strong> {time}</p>
                <p><strong>⏱️ Durata:</strong> {duration} minuti</p>
            </div>
            
            <p>Preparati per la sessione e assicurati di avere una buona connessione internet.</p>
            
            <a href="{action_url}" class="button">Vai alla Prenotazione</a>
            
            <p style="margin-top: 30px; font-size: 14px; color: #666;">
                💡 <strong>Suggerimento:</strong> Testa audio e video prima dell'inizio per evitare problemi tecnici.
            </p>
        </div>
        <div class="footer">
            <p>Questa è un'email automatica da Helpy. Non rispondere a questo messaggio.</p>
        </div>
    </div>
</body>
</html>
""",
            'reminder_10min.html': """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #ffebee; padding: 30px; border-radius: 0 0 10px 10px; }}
        .button {{ display: inline-block; background: #e74c3c; color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; margin: 20px 0; font-size: 18px; font-weight: bold; }}
        .details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #e74c3c; }}
        .urgent {{ background: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107; margin: 20px 0; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⏰ Consulenza in Partenza!</h1>
        </div>
        <div class="content">
            <p>Ciao <strong>{user_name}</strong>,</p>
            <p style="font-size: 18px; font-weight: bold; color: #e74c3c;">La tua consulenza inizia tra 10 MINUTI!</p>
            
            <div class="details">
                <p><strong>👥 Con:</strong> {other_user_name}</p>
                <p><strong>🕐 Orario:</strong> {time}</p>
                <p><strong>⏱️ Durata:</strong> {duration} minuti</p>
            </div>
            
            <div class="urgent">
                <p style="margin: 0; font-weight: bold;">⚠️ Preparati a confermare la tua presenza!</p>
                <p style="margin: 5px 0 0 0; font-size: 14px;">Tra pochi minuti potrai accedere alla stanza virtuale.</p>
            </div>
            
            <a href="{action_url}" class="button">🚀 Entra nella Stanza</a>
            
            <p style="margin-top: 30px; font-size: 14px; color: #666;">
                ✅ Controlla che audio e video funzionino correttamente<br>
                ✅ Trova un luogo tranquillo e senza distrazioni<br>
                ✅ Tieni a portata di mano eventuali documenti necessari
            </p>
        </div>
        <div class="footer">
            <p>Questa è un'email automatica da Helpy. Non rispondere a questo messaggio.</p>
        </div>
    </div>
</body>
</html>
""",
            'community_contact.html': """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #667eea; }}
        .footer {{ text-align: center; margin-top: 20px; color: #888; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💬 Nuovo Messaggio dalla Community</h1>
        </div>
        <div class="content">
            <p>Ciao <strong>{author_name}</strong>,</p>
            <p style="font-size: 16px;">Qualcuno è interessato alla tua domanda e vuole contattarti!</p>
            
            <div class="details">
                <p><strong>👤 Chi:</strong> {contact_name}</p>
                <p><strong>📝 La tua domanda:</strong> {question_title}</p>
                <p><strong>📅 Quando:</strong> {contact_date}</p>
            </div>
            
            <p>Riceverai i suoi messaggi nella sezione chat di Helpy.</p>
            
            <a href="{action_url}" class="button">💬 Apri Chat</a>
            
            <p style="margin-top: 30px; font-size: 14px; color: #666;">
                Rispondi velocemente per aumentare le tue possibilità di ricevere una consulenza! 🚀
            </p>
        </div>
        <div class="footer">
            <p>Questa è un'email automatica da Helpy. Non rispondere a questo messaggio.</p>
        </div>
    </div>
</body>
</html>
"""
        }
        
        template_html = templates.get(template_name)
        
        if not template_html:
            logger.error(f"Template {template_name} non trovato")
            return None
        
        # Sostituisci le variabili nel template
        html_content = template_html
        for key, value in data.items():
            html_content = html_content.replace(f"{{{key}}}", str(value))
        
        return html_content
        
    except Exception as e:
        logger.error(f"Errore generazione HTML template {template_name}: {e}")
        return None
