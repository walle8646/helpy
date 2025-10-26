import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.logger_config import logger
import random
import string

def generate_verification_code() -> str:
    """Genera codice di verifica a 6 cifre"""
    return ''.join(random.choices(string.digits, k=6))

def send_verification_email(to_email: str, code: str, nome: str = "User") -> bool:
    """Invia email di verifica tramite SMTP (SendGrid)"""
    
    # ✅ Usa variabili SMTP dal .env (o hardcoded)
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("EMAIL_FROM")
    
    try:
        # Crea messaggio HTML
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Conferma la tua email - Helpy'
        msg['From'] = from_email
        msg['To'] = to_email
        
        html_body = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8f9fa; border-radius: 10px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #667eea; margin: 0;">✨ Helpy</h1>
            </div>
            
            <div style="background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <h2 style="color: #1a1a1a; margin-top: 0;">Ciao {nome}! 👋</h2>
                
                <p style="color: #666; font-size: 16px; line-height: 1.6;">
                    Grazie per esserti registrato su <strong>Helpy</strong>!
                </p>
                
                <p style="color: #666; font-size: 16px; line-height: 1.6;">
                    Per completare la registrazione, inserisci questo codice di verifica:
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <div style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px 40px; border-radius: 10px; font-size: 32px; font-weight: bold; letter-spacing: 8px;">
                        {code}
                    </div>
                </div>
                
                <p style="color: #999; font-size: 14px; line-height: 1.6; margin-top: 30px;">
                    Questo codice è valido per <strong>15 minuti</strong>.
                </p>
                
                <p style="color: #999; font-size: 14px; line-height: 1.6;">
                    Se non hai richiesto questa registrazione, ignora questa email.
                </p>
            </div>
            
            <div style="text-align: center; margin-top: 30px; color: #999; font-size: 12px;">
                <p>© 2024 Helpy. Tutti i diritti riservati.</p>
            </div>
        </div>
        '''
        
        # Aggiungi parte HTML
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        # ✅ Connetti e invia tramite SMTP
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()  # TLS encryption
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        logger.info(f"✅ Verification email sent to {to_email} via SMTP")
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to send verification email to {to_email}: {e}")
        return False