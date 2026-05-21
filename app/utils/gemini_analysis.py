"""
Servizio di analisi video contestazioni tramite Google Gemini.
Scarica il video MP4 da S3, lo invia a Gemini per l'analisi e restituisce il verdetto.
"""
import os
import json
import time
import tempfile
import boto3
from google import genai
from app.logger_config import logger


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

ANALYSIS_PROMPT = """Sei un analista imparziale per una piattaforma di consulenze online chiamata Ispiramy.
Ti viene fornito il video di una consulenza in videochiamata e le seguenti informazioni:

**Descrizione della consulenza richiesta dal cliente:**
{booking_description}

**Motivo della contestazione aperta dal cliente:**
{dispute_description}

**Informazioni sulla consulenza:**
- Consulente: {consultant_name}
- Cliente: {client_name}
- Data: {booking_date}
- Durata prevista: {booking_time}

Analizza il video della consulenza e valuta:
1. Il consulente ha affrontato l'argomento richiesto dal cliente?
2. Il consulente ha dato risposte concrete e utili o è stato evasivo/impreparato?
3. La contestazione del cliente è giustificata in base a quanto avvenuto nel video?
4. Il consulente si è comportato in modo professionale e rispettoso?

Rispondi ESCLUSIVAMENTE con un JSON valido (senza markdown, senza ```json) nel seguente formato:
{{
    "verdict": "justified" oppure "unjustified" oppure "uncertain",
    "confidence": numero da 0 a 100,
    "comment": "Commento dettagliato in italiano che spiega il verdetto, citando momenti specifici del video come evidenza. Massimo 1000 caratteri."
}}

Dove:
- "justified" = la contestazione del cliente è giustificata (il consulente non ha soddisfatto la richiesta)
- "unjustified" = la contestazione NON è giustificata (il consulente ha svolto correttamente il suo lavoro)
- "uncertain" = non è possibile determinare con sicurezza
- "confidence" = percentuale di sicurezza del tuo verdetto (0-100)
- "comment" = spiegazione dettagliata in italiano"""


def analyze_dispute_video(
    video_path: str,
    booking_description: str,
    dispute_description: str,
    consultant_name: str,
    client_name: str,
    booking_date: str,
    booking_time: str,
) -> dict:
    """
    Analizza un video di consulenza con Gemini e restituisce il verdetto.
    
    Returns:
        dict con chiavi: verdict, confidence, comment
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY non configurata")

    client = genai.Client(api_key=GEMINI_API_KEY)

    # Upload video a Gemini
    logger.info(f"Upload video a Gemini: {video_path}")
    video_file = client.files.upload(file=video_path)
    logger.info(f"Video caricato: {video_file.name}, stato: {video_file.state}")

    # Attendi che Gemini finisca il processing
    max_wait = 300  # 5 minuti max
    waited = 0
    while video_file.state.name == "PROCESSING" and waited < max_wait:
        time.sleep(10)
        waited += 10
        video_file = client.files.get(name=video_file.name)
        logger.info(f"Video processing... ({waited}s), stato: {video_file.state}")

    if video_file.state.name == "FAILED":
        raise RuntimeError(f"Gemini ha fallito il processing del video: {video_file.state}")
    
    if video_file.state.name == "PROCESSING":
        raise RuntimeError("Timeout: il video è ancora in processing dopo 5 minuti")

    # Prepara il prompt
    prompt = ANALYSIS_PROMPT.format(
        booking_description=booking_description or "Non specificata",
        dispute_description=dispute_description,
        consultant_name=consultant_name,
        client_name=client_name,
        booking_date=booking_date,
        booking_time=booking_time,
    )

    # Invia al modello
    logger.info("Invio richiesta di analisi a Gemini 2.5 Flash...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[video_file, prompt],
    )

    # Parse risposta JSON
    response_text = response.text.strip()
    # Rimuovi eventuale wrapping markdown
    if response_text.startswith("```"):
        response_text = response_text.split("\n", 1)[1]
        if response_text.endswith("```"):
            response_text = response_text[:-3].strip()

    logger.info(f"Risposta Gemini: {response_text[:500]}")

    result = json.loads(response_text)

    # Validazione
    if result.get("verdict") not in ("justified", "unjustified", "uncertain"):
        result["verdict"] = "uncertain"
    result["confidence"] = max(0, min(100, int(result.get("confidence", 50))))
    result["comment"] = str(result.get("comment", ""))[:5000]

    # Cleanup: elimina il file da Gemini
    try:
        client.files.delete(name=video_file.name)
    except Exception:
        pass

    return result


def download_video_from_s3(booking_id: int) -> str:
    """
    Scarica il video MP4 di un booking da S3 in un file temporaneo.
    
    Returns:
        Path del file temporaneo scaricato
    """
    s3_client = boto3.client(
        's3',
        region_name=os.getenv("AWS_S3_REGION", "eu-north-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    bucket = os.getenv("AWS_S3_BUCKET_NAME")

    # Cerca il file MP4
    prefix = f"booking_{booking_id}/"
    resp = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    mp4_key = None
    for obj in resp.get("Contents", []):
        if obj["Key"].endswith(".mp4"):
            mp4_key = obj["Key"]
            break

    if not mp4_key:
        raise FileNotFoundError(f"Nessun file MP4 trovato per booking {booking_id}")

    # Scarica in file temporaneo
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    logger.info(f"Download S3: {mp4_key} → {tmp.name}")
    s3_client.download_file(bucket, mp4_key, tmp.name)
    tmp.close()

    return tmp.name
