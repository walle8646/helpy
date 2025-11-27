"""
Agora Cloud Recording Integration
Gestisce l'avvio, arresto e acquisizione delle registrazioni video
"""

import os
import time
import requests
import base64
import boto3
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from app.utils.agora_token import generate_access_token

load_dotenv()

logger = logging.getLogger(__name__)

# Credenziali Agora per le chiamate video (App ID + App Certificate)
AGORA_APP_ID = os.getenv("AGORA_APP_ID")
AGORA_APP_CERTIFICATE = os.getenv("AGORA_APP_CERTIFICATE")

# Credenziali Agora REST API per Cloud Recording (Customer ID + Customer Secret)
# Questi sono diversi dall'App ID e App Certificate!
AGORA_CUSTOMER_ID = os.getenv("AGORA_CUSTOMER_ID")
AGORA_CUSTOMER_SECRET = os.getenv("AGORA_CUSTOMER_SECRET")

# Credenziali AWS S3
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")
AWS_S3_REGION = os.getenv("AWS_S3_REGION", "eu-south-1")

# Agora Cloud Recording API
AGORA_RECORDING_API = "https://api.agora.io/v1/apps/{}/cloud_recording"

# Mappa delle regioni AWS a codici Agora Cloud Recording
# https://docs.agora.io/en/cloud-recording/reference/cloud-recording-api?platform=RESTful#region-codes
AWS_TO_AGORA_REGION = {
    "us-east-1": 1,        # US
    "us-west-2": 2,        # US
    "eu-west-1": 3,        # EU
    "eu-central-1": 4,     # EU
    "eu-south-1": 9,       # EU (Milan)
    "eu-north-1": 10,      # EU (Stockholm)
    "ap-southeast-1": 5,   # Asia
    "ap-northeast-1": 6,   # Asia
    "ap-south-1": 7,       # Asia
    "sa-east-1": 8,        # South America
}


def get_agora_region_code(aws_region: str) -> int:
    """
    Converte una regione AWS in codice Agora Cloud Recording.
    
    Args:
        aws_region: Regione AWS (es: "eu-south-1")
    
    Returns:
        Codice regione Agora (numero intero)
    """
    code = AWS_TO_AGORA_REGION.get(aws_region)
    if code is None:
        logger.warning(f"⚠️ Region {aws_region} not found in mapping, defaulting to 9 (EU Milan)")
        return 9
    return code

def get_agora_auth_header() -> str:
    """Genera l'header di autenticazione per le API Agora usando App ID e Certificate"""
    # Usa App ID come username e App Certificate come password per Basic Auth
    credentials = f"{AGORA_CUSTOMER_ID}:{AGORA_CUSTOMER_SECRET}"
    logger.info(f"🔐 [auth] Creating Basic Auth with:")
    logger.info(f"   - AGORA_CUSTOMER_ID: {AGORA_CUSTOMER_ID}")
    logger.info(f"   - AGORA_CUSTOMER_SECRET: {AGORA_CUSTOMER_SECRET[:20]}...")
    encoded = base64.b64encode(credentials.encode()).decode()
    logger.info(f"   - Encoded header: Basic {encoded[:30]}...")
    return f"Basic {encoded}"


def _extract_recording_file_info(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Estrae le informazioni del file dal payload di risposta Agora."""
    server_response = data.get("serverResponse", {})
    file_list = server_response.get("fileList", [])

    if not file_list:
        logger.warning("⚠️ Nessun file presente nella risposta della registrazione")
        return None

    recording_file = file_list[0]

    return {
        "file_name": recording_file.get("fileName"),
        "track_type": recording_file.get("trackType"),
        "uid": recording_file.get("uid"),
        "mix_duration": recording_file.get("mixedAllUser"),
        "is_playable": recording_file.get("isPlayable"),
        "slice_start_time": recording_file.get("sliceStartTime"),
    }


def query_recording(resource_id: str, sid: str, channel_name: str, uid: int) -> Optional[Dict[str, Any]]:
    """Interroga lo stato della registrazione per recuperare la lista dei file."""
    try:
        query_url = f"{AGORA_RECORDING_API.format(AGORA_APP_ID)}/resourceid/{resource_id}/sid/{sid}/mode/mix/query"
        params = {
            "cname": channel_name,
            "uid": str(uid)
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": get_agora_auth_header()
        }

        logger.info(f"🔎 [query_recording] Querying status for SID: {sid}")
        response = requests.get(query_url, params=params, headers=headers)
        logger.info(f"🔎 [query_recording] Response status: {response.status_code}")
        logger.info(f"🔎 [query_recording] Response body: {response.text}")

        if response.status_code != 200:
            logger.error(f"❌ [query_recording] Error {response.status_code}: {response.text}")
            return None

        data = response.json()
        logger.info(f"🔎 [query_recording] Full response: {data}")

        result = _extract_recording_file_info(data)
        if result:
            logger.info(f"✅ [query_recording] File retrieved via query: {result['file_name']}")
        return result

    except Exception as exc:
        logger.error(f"❌ [query_recording] Exception: {exc}")
        return None


def start_recording(channel_name: str, uid: int, rtc_token: str) -> Optional[Dict[str, Any]]:
    """
    Avvia la registrazione cloud per un canale Agora
    
    Args:
        channel_name: Nome del canale (es: "booking_123")
        uid: User ID per il bot recorder
        rtc_token: Token RTC Agora valido per il canale (usato per la registrazione)
    
    Returns:
        Dict con sid e resource_id se successo, None se errore
    """
    try:
        logger.info(f"🎬 [start_recording] Starting for channel: {channel_name}")
        logger.info(f"   - AWS_S3_BUCKET_NAME: {AWS_S3_BUCKET_NAME}")
        logger.info(f"   - AWS_S3_REGION: {AWS_S3_REGION}")
        
        # Step 1: Acquire resource
        acquire_url = AGORA_RECORDING_API.format(AGORA_APP_ID) + "/acquire"
        logger.info(f"   - Acquire URL: {acquire_url}")
        
        acquire_payload = {
            "cname": channel_name,
            "uid": str(uid),
            "clientRequest": {
                "resourceExpiredHour": 24
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": get_agora_auth_header()
        }
        
        logger.info(f"🔄 [acquire] Sending request...")
        response = requests.post(acquire_url, json=acquire_payload, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"❌ [acquire] Error {response.status_code}: {response.text}")
            return None
        
        logger.info(f"✓ [acquire] Response 200 OK")
        resource_id = response.json().get("resourceId")
        
        if not resource_id:
            logger.error(f"❌ [acquire] No resourceId in response: {response.json()}")
            return None
        
        logger.info(f"✓ [acquire] Got resourceId: {resource_id}")

        
        # Step 2: Start recording with Access Token
        start_url = f"{AGORA_RECORDING_API.format(AGORA_APP_ID)}/resourceid/{resource_id}/mode/mix/start"
        logger.info(f"   - Start URL: {start_url}")
        
        # Genera Access Token per Cloud Recording API (non RTC Token!)
        access_token = generate_access_token(expiration_seconds=3600)
        logger.info(f"🔐 [start] Generated Access Token for Cloud Recording API")
        
        start_payload = {
            "cname": channel_name,
            "uid": str(uid),
            "clientRequest": {
                "token": access_token,  # Access Token, non RTC Token!
                "recordingConfig": {
                    "channelType": 0,  # 0 = communication, 1 = live broadcast
                    "streamMode": "default",
                    "videoStreamType": 0,
                    "maxIdleTime": 300,  # 5 minutes - increased from 30 to handle longer calls
                    "transcodingConfig": {
                        "width": 1280,
                        "height": 720,
                        "fps": 30,
                        "bitrate": 2000,
                        "mixedVideoLayout": 1  # 1 = floating layout
                    }
                },
                "storageConfig": {
                    "vendor": 1,  # 1 = AWS S3
                    "region": get_agora_region_code(AWS_S3_REGION),  # Codice numerico per Agora
                    "bucket": AWS_S3_BUCKET_NAME,
                    "accessKey": AWS_ACCESS_KEY_ID,
                    "secretKey": AWS_SECRET_ACCESS_KEY
                    # NO fileNamePrefix - non supportato da Agora API
                }
            }
        }
        
        logger.info(f"🔄 [start] Sending start request with storageConfig:")
        logger.info(f"   - bucket: {AWS_S3_BUCKET_NAME}")
        logger.info(f"   - region: {AWS_S3_REGION} (Agora code: {get_agora_region_code(AWS_S3_REGION)})")
        logger.info(f"   - token: Access Token (for Cloud Recording API)")
        logger.info(f"   - Full payload: {start_payload}")
        
        response = requests.post(start_url, json=start_payload, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"❌ [start] Error {response.status_code}: {response.text}")
            return None
        
        logger.info(f"✓ [start] Response 200 OK")
        data = response.json()
        sid = data.get("sid")
        
        logger.info(f"✅ [start_recording] Recording avviato - SID: {sid}, ResourceID: {resource_id}")
        
        return {
            "sid": sid,
            "resource_id": resource_id
        }
    
    except Exception as e:
        logger.error(f"❌ [start_recording] Exception: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def stop_recording(resource_id: str, sid: str, channel_name: str, uid: int) -> Optional[Dict[str, Any]]:
    """
    Ferma la registrazione cloud
    
    Args:
        resource_id: Resource ID ottenuto dall'acquire
        sid: Session ID ottenuto dallo start
        channel_name: Nome del canale
        uid: User ID del bot recorder
    
    Returns:
        Dict con info sul file registrato se successo, None se errore
    """
    try:
        stop_url = f"{AGORA_RECORDING_API.format(AGORA_APP_ID)}/resourceid/{resource_id}/sid/{sid}/mode/mix/stop"
        
        stop_payload = {
            "cname": channel_name,
            "uid": str(uid),
            "clientRequest": {}
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": get_agora_auth_header()
        }
        
        logger.info(f"\n🛑 [stop_recording] Starting stop for SID: {sid}")
        logger.info(f"   - Stop URL: {stop_url}")
        logger.info(f"   - Channel: {channel_name}")
        logger.info(f"   - UID: {uid}")
        
        response = requests.post(stop_url, json=stop_payload, headers=headers)
        
        logger.info(f"🛑 [stop_recording] Response status: {response.status_code}")
        logger.info(f"🛑 [stop_recording] Response body: {response.text}")
        
        if response.status_code == 404:
            logger.warning(f"⚠️ [stop] Worker not found (404) - Recording was auto-stopped (empty channel)")
            logger.info("🔄 [stop_recording] Attempting to retrieve recording details via query after auto-stop")
            query_result = query_recording(resource_id, sid, channel_name, uid)
            if query_result:
                logger.info(f"✅ [stop_recording] Recording info recovered via query: {query_result['file_name']}")
            else:
                logger.warning("⚠️ [stop_recording] Unable to recover recording info after auto-stop on first attempt")
                logger.info("🔄 [stop_recording] Retrying query in 5 seconds...")
                time.sleep(5)
                query_result = query_recording(resource_id, sid, channel_name, uid)
                if query_result:
                    logger.info(f"✅ [stop_recording] Recording info recovered on retry: {query_result['file_name']}")
                else:
                    logger.warning("⚠️ [stop_recording] Second query attempt also failed to retrieve recording info")
            return query_result

        if response.status_code == 400:
            logger.error(f"❌ [stop] Bad request stopping recording: {response.text}")
            try:
                error_payload = response.json()
                logger.error(f"❌ [stop] Parsed error payload: {error_payload}")
            except ValueError:
                logger.error("❌ [stop] Response body is not valid JSON")
            return None
        
        if response.status_code != 200:
            logger.error(f"❌ Errore stop recording: {response.status_code} - {response.text}")
            return None
        
        data = response.json()
        logger.info(f"🛑 [stop_recording] Full response: {data}")

        result = _extract_recording_file_info(data)
        if result:
            logger.info(f"✅ Recording fermato - File: {result['file_name']}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Errore in stop_recording: {str(e)}")
        return None


def get_recording_url(file_name: str) -> str:
    """
    Genera URL firmato per accedere al file registrato su S3
    
    Args:
        file_name: Nome del file su S3
    
    Returns:
        URL firmato valido per 7 giorni
    """
    try:
        s3_client = boto3.client(
            's3',
            region_name=AWS_S3_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        
        # Genera URL firmato valido per 7 giorni
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': AWS_S3_BUCKET_NAME, 'Key': file_name},
            ExpiresIn=604800  # 7 giorni in secondi
        )
        
        return url
        
    except Exception as e:
        logger.error(f"❌ Errore generazione URL: {str(e)}")
        return ""
