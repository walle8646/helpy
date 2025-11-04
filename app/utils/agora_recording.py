"""
Agora Cloud Recording Integration
Gestisce l'avvio, arresto e acquisizione delle registrazioni video
"""

import os
import requests
import base64
import boto3
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Credenziali Agora
AGORA_APP_ID = os.getenv("AGORA_APP_ID")
AGORA_APP_CERTIFICATE = os.getenv("AGORA_APP_CERTIFICATE")

# Per Cloud Recording, Agora usa App ID come Customer ID
# e genera il Customer Secret dall'App Certificate
AGORA_CUSTOMER_ID = AGORA_APP_ID
AGORA_CUSTOMER_SECRET = AGORA_APP_CERTIFICATE

# Credenziali AWS S3
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")
AWS_S3_REGION = os.getenv("AWS_S3_REGION", "eu-south-1")

# Agora Cloud Recording API
AGORA_RECORDING_API = "https://api.agora.io/v1/apps/{}/cloud_recording"


def get_agora_auth_header() -> str:
    """Genera l'header di autenticazione per le API Agora usando App ID e Certificate"""
    # Usa App ID come username e App Certificate come password per Basic Auth
    credentials = f"{AGORA_CUSTOMER_ID}:{AGORA_CUSTOMER_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


def start_recording(channel_name: str, uid: int, token: str) -> Optional[Dict[str, Any]]:
    """
    Avvia la registrazione cloud per un canale Agora
    
    Args:
        channel_name: Nome del canale (es: "booking_123")
        uid: User ID per il bot recorder
        token: Token Agora valido per il canale
    
    Returns:
        Dict con sid e resource_id se successo, None se errore
    """
    try:
        # Step 1: Acquire resource
        acquire_url = AGORA_RECORDING_API.format(AGORA_APP_ID) + "/acquire"
        
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
        
        response = requests.post(acquire_url, json=acquire_payload, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Errore acquire: {response.status_code} - {response.text}")
            return None
        
        resource_id = response.json().get("resourceId")
        
        if not resource_id:
            print("❌ Nessun resourceId ottenuto")
            return None
        
        # Step 2: Start recording
        start_url = f"{AGORA_RECORDING_API.format(AGORA_APP_ID)}/resourceid/{resource_id}/mode/mix/start"
        
        start_payload = {
            "cname": channel_name,
            "uid": str(uid),
            "clientRequest": {
                "token": token,
                "recordingConfig": {
                    "channelType": 0,  # 0 = communication, 1 = live broadcast
                    "streamMode": "default",
                    "videoStreamType": 0,
                    "maxIdleTime": 30,
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
                    "region": AWS_S3_REGION,
                    "bucket": AWS_S3_BUCKET_NAME,
                    "accessKey": AWS_ACCESS_KEY_ID,
                    "secretKey": AWS_SECRET_ACCESS_KEY,
                    "fileNamePrefix": [f"recordings/{channel_name}"]
                }
            }
        }
        
        response = requests.post(start_url, json=start_payload, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Errore start recording: {response.status_code} - {response.text}")
            return None
        
        data = response.json()
        sid = data.get("sid")
        
        print(f"✅ Recording avviato - SID: {sid}, ResourceID: {resource_id}")
        
        return {
            "sid": sid,
            "resource_id": resource_id
        }
        
    except Exception as e:
        print(f"❌ Errore in start_recording: {str(e)}")
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
        
        response = requests.post(stop_url, json=stop_payload, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Errore stop recording: {response.status_code} - {response.text}")
            return None
        
        data = response.json()
        server_response = data.get("serverResponse", {})
        
        file_list = server_response.get("fileList", [])
        
        if not file_list:
            print("⚠️ Nessun file registrato trovato")
            return None
        
        # Prendi il primo file (normalmente c'è solo un file MP4)
        recording_file = file_list[0]
        
        print(f"✅ Recording fermato - File: {recording_file.get('fileName')}")
        
        return {
            "file_name": recording_file.get("fileName"),
            "track_type": recording_file.get("trackType"),
            "uid": recording_file.get("uid"),
            "mix_duration": recording_file.get("mixedAllUser"),
            "is_playable": recording_file.get("isPlayable"),
            "slice_start_time": recording_file.get("sliceStartTime")
        }
        
    except Exception as e:
        print(f"❌ Errore in stop_recording: {str(e)}")
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
        print(f"❌ Errore generazione URL: {str(e)}")
        return ""
