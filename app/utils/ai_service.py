"""
Servizio AI per generazione automatica di aree di interesse e tag
Utilizza OpenAI GPT per analizzare la descrizione del profilo utente
"""
import os
import json
from openai import OpenAI
from app.logger_config import logger

# Client OpenAI — richiede OPENAI_API_KEY nel .env
_client = None

def _get_client() -> OpenAI:
    """Restituisce il client OpenAI, inizializzandolo al primo utilizzo"""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY non configurata. Aggiungi la chiave nelle variabili d'ambiente.")
        _client = OpenAI(api_key=api_key)
    return _client


async def genera_aree_interesse(descrizione: str, professione: str = None) -> list[str]:
    """
    Genera automaticamente le aree di interesse basandosi sulla descrizione del profilo.
    
    Args:
        descrizione: la descrizione/bio dell'utente
        professione: la professione dell'utente (opzionale)
    
    Returns:
        Lista di aree di interesse (stringhe)
    """
    try:
        client = _get_client()
        
        prompt_context = f"Descrizione del profilo: {descrizione}"
        if professione:
            prompt_context += f"\nProfessione: {professione}"
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sei un assistente che analizza profili professionali su una piattaforma di consulenze italiana. "
                        "Dato il testo del profilo di un utente, genera una lista di 5-8 aree di interesse/competenza "
                        "pertinenti e specifiche. Le aree devono essere in italiano, concise (2-4 parole ciascuna), "
                        "e separate da virgole. Non aggiungere numerazione, punti elenco o spiegazioni. "
                        "Rispondi SOLO con le aree separate da virgola."
                    )
                },
                {
                    "role": "user",
                    "content": prompt_context
                }
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        result = response.choices[0].message.content.strip()
        # Pulizia: rimuovi eventuale punteggiatura finale e split
        aree = [a.strip().rstrip('.') for a in result.split(',') if a.strip()]
        
        logger.info(f"🤖 Aree di interesse generate: {aree}")
        return aree
        
    except ValueError as e:
        logger.error(f"❌ Errore configurazione AI: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Errore generazione aree di interesse: {e}")
        raise


async def genera_tags(descrizione: str, aree_interesse: str = None, professione: str = None) -> list[str]:
    """
    Genera tag di ricerca basandosi sulla descrizione e sulle aree di interesse.
    I tag vengono salvati nel DB e utilizzati per migliorare la ricerca sul sito.
    
    Args:
        descrizione: la descrizione/bio dell'utente
        aree_interesse: le aree di interesse (stringa separata da virgole)
        professione: la professione dell'utente (opzionale)
    
    Returns:
        Lista di tag (stringhe lowercase, senza spazi extra)
    """
    try:
        client = _get_client()
        
        prompt_context = f"Descrizione del profilo: {descrizione}"
        if aree_interesse:
            prompt_context += f"\nAree di interesse: {aree_interesse}"
        if professione:
            prompt_context += f"\nProfessione: {professione}"
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sei un assistente che genera tag di ricerca per profili professionali su una piattaforma "
                        "di consulenze italiana. Dato il profilo di un utente, genera 10-15 tag di ricerca pertinenti "
                        "che permettano ad altri utenti di trovare questo consulente. "
                        "I tag devono essere:\n"
                        "- In italiano\n"
                        "- Tutti in minuscolo\n"
                        "- Brevi (1-3 parole massimo)\n"
                        "- Specifici e rilevanti per la ricerca\n"
                        "- Un mix di termini generali e specifici\n"
                        "Rispondi SOLO con un JSON array di stringhe, esempio: [\"tag1\", \"tag2\", \"tag3\"]"
                    )
                },
                {
                    "role": "user",
                    "content": prompt_context
                }
            ],
            temperature=0.5,
            max_tokens=300
        )
        
        result = response.choices[0].message.content.strip()
        
        # Parsing del JSON array
        try:
            tags = json.loads(result)
            if not isinstance(tags, list):
                raise ValueError("Risposta non è una lista")
        except json.JSONDecodeError:
            # Fallback: prova a pulire la risposta
            result = result.strip('`').strip()
            if result.startswith('json'):
                result = result[4:].strip()
            tags = json.loads(result)
        
        # Normalizza: lowercase, strip, rimuovi duplicati
        tags = list(dict.fromkeys(t.strip().lower() for t in tags if t.strip()))
        
        logger.info(f"🏷️ Tags generati: {tags}")
        return tags
        
    except ValueError as e:
        logger.error(f"❌ Errore configurazione AI: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Errore generazione tags: {e}")
        raise
