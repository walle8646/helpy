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
    
    # ✅ Usa variabili SMTP dal .env
    smtp_host = os.getenv("SMTP_SERVER") or os.getenv("SMTP_HOST")  # Supporta entrambi i nomi
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("FROM_EMAIL") or os.getenv("EMAIL_FROM")  # Supporta entrambi i nomi
    
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

def send_profile_verification_request(to_email: str, user_id: int, user_name: str, user_email: str) -> bool:
    """Invia email ai verifiers quando un utente modifica il profilo e soddisfa i requisiti"""
    
    logger.info(f"🔍 DEBUG - send_profile_verification_request called")
    logger.info(f"  - to_email: {to_email}")
    logger.info(f"  - user_id: {user_id}")
    logger.info(f"  - user_name: {user_name}")
    logger.info(f"  - user_email: {user_email}")
    
    # ✅ Usa variabili SMTP dal .env (supporta sia SMTP_SERVER che SMTP_HOST)
    smtp_host = os.getenv("SMTP_SERVER") or os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("FROM_EMAIL") or os.getenv("EMAIL_FROM")
    
    logger.info(f"🔍 DEBUG - SMTP Configuration:")
    logger.info(f"  - SMTP_HOST: {smtp_host}")
    logger.info(f"  - SMTP_PORT: {smtp_port}")
    logger.info(f"  - SMTP_USER: {smtp_user}")
    logger.info(f"  - EMAIL_FROM: {from_email}")
    logger.info(f"  - SMTP_PASSWORD: {'*' * len(smtp_password) if smtp_password else 'NOT SET'}")
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'Richiesta Verifica Profilo - {user_name}'
        msg['From'] = from_email
        msg['To'] = to_email
        
        html_body = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8f9fa; border-radius: 10px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #667eea; margin: 0;">✨ Helpy - Richiesta Verifica</h1>
            </div>
            
            <div style="background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <h2 style="color: #1a1a1a; margin-top: 0;">Nuovo Profilo da Verificare 🔍</h2>
                
                <p style="color: #666; font-size: 16px; line-height: 1.6;">
                    L'utente <strong>{user_name}</strong> ha aggiornato il proprio profilo e ha completato tutti i requisiti per la verifica:
                </p>
                
                <ul style="color: #666; font-size: 16px; line-height: 1.8;">
                    <li>✅ Professione specificata</li>
                    <li>✅ Categoria selezionata</li>
                    <li>✅ Aree di interesse definite</li>
                    <li>✅ Descrizione completa (minimo 200 caratteri)</li>
                </ul>
                
                <div style="background: #f8f9fa; padding: 15px; border-left: 4px solid #667eea; margin: 20px 0;">
                    <p style="margin: 0; color: #666;"><strong>Email utente:</strong> {user_email}</p>
                    <p style="margin: 10px 0 0 0; color: #666;"><strong>ID utente:</strong> {user_id}</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="http://localhost:8000/user/{user_id}" 
                       style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold;">
                        Visualizza Profilo
                    </a>
                </div>
                
                <p style="color: #999; font-size: 14px; line-height: 1.6; margin-top: 30px;">
                    Accedi al pannello di amministrazione per verificare il profilo e assegnare il badge verificato.
                </p>
            </div>
            
            <div style="text-align: center; margin-top: 30px; color: #999; font-size: 12px;">
                <p>© 2024 Helpy. Tutti i diritti riservati.</p>
            </div>
        </div>
        '''
        
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        logger.info(f"📧 Connecting to SMTP server {smtp_host}:{smtp_port}...")
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            logger.info("🔐 Starting TLS...")
            server.starttls()
            logger.info("🔑 Logging in...")
            server.login(smtp_user, smtp_password)
            logger.info("📤 Sending message...")
            server.send_message(msg)
        
        logger.info(f"✅ Profile verification request sent to {to_email} for user {user_name} (ID: {user_id})")
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to send profile verification request to {to_email}: {e}", exc_info=True)
        return False