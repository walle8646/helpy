import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from app.logger_config import logger
import random
import string

def generate_verification_code() -> str:
    """Genera codice di verifica a 6 cifre"""
    return ''.join(random.choices(string.digits, k=6))

def send_verification_email(to_email: str, code: str, nome: str = "User") -> bool:
    """Invia email di verifica tramite SendGrid API HTTP"""
    
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY") or os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("FROM_EMAIL") or os.getenv("EMAIL_FROM")
    
    if not sendgrid_api_key or not from_email:
        logger.error("❌ SendGrid API key or FROM_EMAIL not configured")
        return False
    
    try:
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
        
        message = Mail(
            from_email=Email(from_email),
            to_emails=To(to_email),
            subject='Conferma la tua email - Helpy',
            html_content=Content("text/html", html_body)
        )
        
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        
        logger.info(f"✅ Verification email sent to {to_email} via SendGrid API (status: {response.status_code})")
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to send verification email to {to_email}: {e}", exc_info=True)
        return False

def send_profile_verification_request(to_email: str, user_id: int, user_name: str, user_email: str) -> bool:
    """Invia email ai verifiers quando un utente modifica il profilo e soddisfa i requisiti"""
    
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY") or os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("FROM_EMAIL") or os.getenv("EMAIL_FROM")
    
    if not sendgrid_api_key or not from_email:
        logger.error("❌ SendGrid API key or FROM_EMAIL not configured")
        return False
    
    try:
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
        
        message = Mail(
            from_email=Email(from_email),
            to_emails=To(to_email),
            subject=f'Richiesta Verifica Profilo - {user_name}',
            html_content=Content("text/html", html_body)
        )
        
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        
        logger.info(f"✅ Profile verification request sent to {to_email} for user {user_name} (ID: {user_id}) via SendGrid API (status: {response.status_code})")
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to send profile verification request to {to_email}: {e}", exc_info=True)
        return False