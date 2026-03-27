import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.database import create_db_and_tables
from app.routes import home, auth, consultants, user_profile, messages, community, public_profile, availability, booking, consultation, stripe_webhook, notifications, review, dispute
from app.logger_config import logger
from app.scheduler import start_scheduler, shutdown_scheduler
from app.utils.template_helpers import get_all_categories
from app.utils_user import get_display_name, get_default_avatar

app = FastAPI(title="Helpy", version="1.0.0")


# Middleware per aggiungere categorie globalmente ai template
class CategoriesMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Carica categorie e le rende disponibili nel request.state
        request.state.categories = get_all_categories()
        response = await call_next(request)
        return response


# Session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "helpy-super-secret-key-change-in-production-2024"),
    max_age=86400
)

# Aggiungi middleware categorie
app.add_middleware(CategoriesMiddleware)

# Templates
templates = Jinja2Templates(directory="app/templates")
# Aggiungi filtro personalizzato per nomi utenti
templates.env.filters['display_name'] = get_display_name
templates.env.filters['default_avatar'] = get_default_avatar

# Filtro per parsing JSON (usato per le immagini community)
import json as _json
def _parse_json(value):
    """Parse una stringa JSON in un oggetto Python. Ritorna lista vuota se invalido."""
    if not value:
        return []
    try:
        result = _json.loads(value)
        return result if isinstance(result, list) else []
    except (ValueError, TypeError):
        return []
templates.env.filters['parse_json'] = _parse_json

app.state.templates = templates

# Crea directory uploads
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
(UPLOAD_DIR / "profile_pictures").mkdir(exist_ok=True)

# Monta static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include routes
app.include_router(home.router, tags=["home"])
app.include_router(auth.router, tags=["auth"])
app.include_router(user_profile.router, tags=["profile"])
app.include_router(public_profile.router, tags=["public_profile"])
app.include_router(consultants.router, tags=["consultants"])
app.include_router(messages.router, tags=["messages"])  # ✅ Aggiungi questo
app.include_router(community.router)
app.include_router(availability.router, tags=["availability"])
app.include_router(booking.router, tags=["booking"])
app.include_router(consultation.router, tags=["consultation"])
app.include_router(stripe_webhook.router, tags=["webhooks"])
app.include_router(notifications.router, tags=["notifications"])
app.include_router(review.router, tags=["reviews"])
app.include_router(dispute.router, tags=["disputes"])


# Test S3 credentials
def test_s3_credentials():
    """Testa se le credenziali S3 sono valide"""
    try:
        import boto3
        from botocore.exceptions import ClientError
        import sys
        
        aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_s3_bucket_name = os.getenv("AWS_S3_BUCKET_NAME")
        aws_s3_region = os.getenv("AWS_S3_REGION", "eu-south-1")
        
        if not all([aws_access_key_id, aws_secret_access_key, aws_s3_bucket_name]):
            msg = "⚠️ [S3] AWS credentials non configurate completamente"
            print(msg, file=sys.stderr)
            logger.warning(msg)
            return False
        
        msg = "\n🔐 [S3] Testing AWS credentials..."
        print(msg, file=sys.stderr)
        logger.info(msg)
        sys.stderr.flush()
        
        s3_client = boto3.client(
            's3',
            region_name=aws_s3_region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
        
        # Test: head_bucket verifica se il bucket è accessibile
        s3_client.head_bucket(Bucket=aws_s3_bucket_name)
        msg = f"✅ [S3] AWS credentials VALID - Bucket '{aws_s3_bucket_name}' is accessible"
        print(msg, file=sys.stderr)
        logger.info(msg)
        msg2 = f"   Region: {aws_s3_region}"
        print(msg2, file=sys.stderr)
        logger.info(msg2)
        
        # Lista i primi file nel bucket
        try:
            response = s3_client.list_objects_v2(Bucket=aws_s3_bucket_name, MaxKeys=5)
            if 'Contents' in response:
                file_count = response.get('KeyCount', 0)
                msg3 = f"   Files in bucket: {file_count}"
                print(msg3, file=sys.stderr)
                logger.info(msg3)
                if file_count > 0:
                    logger.info(f"   Sample files:")
                    for obj in response['Contents'][:3]:
                        logger.info(f"     - {obj['Key']}")
            else:
                msg4 = f"   Bucket is empty"
                print(msg4, file=sys.stderr)
                logger.info(msg4)
        except Exception as e:
            msg5 = f"   (Could not list files: {str(e)})"
            print(msg5, file=sys.stderr)
            logger.info(msg5)
        
        sys.stderr.flush()
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            msg = f"❌ [S3] ERROR - Bucket '{aws_s3_bucket_name}' does not exist"
            print(msg, file=sys.stderr)
            logger.error(msg)
        elif error_code == 'InvalidAccessKeyId':
            msg = f"❌ [S3] ERROR - Invalid AWS Access Key ID"
            print(msg, file=sys.stderr)
            logger.error(msg)
        elif error_code == 'SignatureDoesNotMatch':
            msg = f"❌ [S3] ERROR - Invalid AWS Secret Access Key"
            print(msg, file=sys.stderr)
            logger.error(msg)
        else:
            msg = f"❌ [S3] ERROR - {error_code}: {str(e)}"
            print(msg, file=sys.stderr)
            logger.error(msg)
        return False
    except Exception as e:
        msg = f"❌ [S3] ERROR - {str(e)}"
        print(msg, file=sys.stderr)
        logger.error(msg)
        return False


# Database init
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    test_s3_credentials()  # Test S3 credentials early
    start_scheduler()  # Avvia lo scheduler per le notifiche programmate
    logger.info("✅ Helpy started successfully")


@app.on_event("shutdown")
def on_shutdown():
    shutdown_scheduler()  # Ferma lo scheduler in modo pulito
    logger.info("👋 Helpy shutting down")


# Esecuzione locale
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)
