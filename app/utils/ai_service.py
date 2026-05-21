"""
Servizio AI per generazione automatica di aree di interesse, tag e moderazione immagini.
Utilizza OpenAI GPT per analizzare profili utente e contenuti della community.
"""
import os
import json
import base64
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


async def modera_immagine(image_base64: str, titolo: str, descrizione: str) -> dict:
    """
    Modera un'immagine caricata nella community tramite GPT-4o vision.
    
    Verifica che l'immagine:
    1. Non sia a sfondo sessuale
    2. Non sia politica
    3. Non sia offensiva/insultante
    4. Non sia pubblicitaria
    5. Sia abbastanza inerente all'argomento della richiesta
    
    Args:
        image_base64: immagine codificata in base64
        titolo: titolo della domanda/richiesta
        descrizione: descrizione della domanda/richiesta
    
    Returns:
        dict con {approved: bool, reason: str}
    """
    try:
        client = _get_client()
        
        # Determina il content type dall'header base64 o usa jpeg come default
        image_data_url = f"data:image/jpeg;base64,{image_base64}"
        
        logger.info(f"🖼️ Avvio moderazione immagine - Titolo: {titolo[:50]}... - Base64 size: {len(image_base64)} chars")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sei un moderatore di contenuti per una piattaforma italiana di consulenze professionali chiamata Ispiramy. "
                        "Analizza l'immagine e verifica che rispetti TUTTE queste regole:\n\n"
                        "1. NON deve contenere contenuti sessuali, nudità o materiale esplicito\n"
                        "2. NON deve contenere propaganda politica, simboli di partiti o messaggi politici\n"
                        "3. NON deve contenere insulti, contenuti offensivi, discriminatori o di odio\n"
                        "4. NON deve essere una pubblicità, un volantino promozionale o spam commerciale\n"
                        "5. DEVE essere ragionevolmente inerente all'argomento della richiesta dell'utente\n\n"
                        "Rispondi ESCLUSIVAMENTE con un oggetto JSON (senza markdown, senza backtick, senza altro testo) "
                        "nel formato: {\"approved\": true, \"reason\": \"Immagine approvata\"} "
                        "oppure {\"approved\": false, \"reason\": \"motivo del rifiuto in italiano\"}"
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"Richiesta dell'utente:\n"
                                f"Titolo: {titolo}\n"
                                f"Descrizione: {descrizione[:500]}\n\n"
                                f"Verifica se l'immagine allegata è appropriata per questa richiesta."
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_data_url,
                                "detail": "low"
                            }
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_tokens=200
        )
        
        # Controlla se la risposta ha contenuto
        choice = response.choices[0]
        
        # Gestisci il caso in cui il modello rifiuta di rispondere (content filter)
        if choice.finish_reason == "content_filter":
            logger.warning("🚫 Moderazione: risposta bloccata dal content filter OpenAI — immagine rifiutata")
            return {"approved": False, "reason": "L'immagine è stata rifiutata dal sistema di moderazione automatica."}
        
        result = choice.message.content
        if not result or not result.strip():
            # Risposta vuota — potrebbe essere un refusal
            refusal = getattr(choice.message, 'refusal', None)
            logger.warning(f"🚫 Moderazione: risposta vuota da OpenAI. Refusal: {refusal}")
            return {"approved": False, "reason": "Impossibile verificare l'immagine. Riprova con un'altra immagine."}
        
        result = result.strip()
        logger.info(f"🖼️ Risposta grezza moderazione: {result[:200]}")
        
        # Parsing JSON — gestisci vari formati di risposta
        moderation_result = None
        
        # Tentativo 1: JSON diretto
        try:
            moderation_result = json.loads(result)
        except json.JSONDecodeError:
            pass
        
        # Tentativo 2: rimuovi backtick markdown
        if moderation_result is None:
            cleaned = result.strip('`').strip()
            if cleaned.startswith('json'):
                cleaned = cleaned[4:].strip()
            try:
                moderation_result = json.loads(cleaned)
            except json.JSONDecodeError:
                pass
        
        # Tentativo 3: cerca un oggetto JSON nella risposta
        if moderation_result is None:
            import re
            json_match = re.search(r'\{[^{}]*"approved"\s*:\s*(true|false)[^{}]*\}', result, re.IGNORECASE)
            if json_match:
                try:
                    moderation_result = json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
        
        # Se ancora non parsato, analizza il testo della risposta
        if moderation_result is None:
            logger.warning(f"⚠️ Moderazione: impossibile parsare JSON dalla risposta: {result[:200]}")
            # Euristica: cerca parole chiave nella risposta
            result_lower = result.lower()
            if any(w in result_lower for w in ["approvata", "approved", "appropriata", "pertinente", "idonea"]):
                moderation_result = {"approved": True, "reason": "Immagine approvata"}
            else:
                moderation_result = {"approved": False, "reason": "Immagine non approvata dalla moderazione automatica."}
        
        approved = moderation_result.get("approved", False)
        reason = moderation_result.get("reason", "Errore nella moderazione")
        
        logger.info(f"🖼️ Moderazione immagine: {'✅ Approvata' if approved else '❌ Rifiutata'} - {reason}")
        return {"approved": approved, "reason": reason}
        
    except Exception as e:
        logger.error(f"❌ Errore moderazione immagine: {e}", exc_info=True)
        # In caso di errore, rifiuta per sicurezza
        return {"approved": False, "reason": "Errore durante la verifica dell'immagine. Riprova più tardi."}


async def valida_richiesta(titolo: str, descrizione: str) -> dict:
    """
    Valida il contenuto di una richiesta nella community tramite AI.
    
    Verifica che il testo sia una richiesta genuina di consulenza/aiuto:
    1. Non sia spam, testo casuale o senza senso
    2. Non contenga insulti, contenuti offensivi o inappropriati
    3. Non sia pubblicità o auto-promozione
    4. Non contenga contenuti politici, sessuali o discriminatori
    5. Esprima una reale volontà di cercare consulenza o aiuto su un argomento
    
    Args:
        titolo: titolo della richiesta
        descrizione: descrizione dettagliata della richiesta
    
    Returns:
        dict con {approved: bool, reason: str}
    """
    try:
        client = _get_client()
        
        logger.info(f"📝 Avvio validazione richiesta - Titolo: {titolo[:50]}...")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sei un moderatore di contenuti per Ispiramy, una piattaforma italiana di consulenze professionali. "
                        "Gli utenti pubblicano richieste nella community per cercare consulenti o aiuto su vari argomenti.\n\n"
                        "Devi verificare che la richiesta rispetti TUTTE queste regole:\n"
                        "1. Deve essere una richiesta GENUINA di consulenza, aiuto o informazioni su un argomento\n"
                        "2. NON deve essere spam, testo casuale, senza senso o test\n"
                        "3. NON deve contenere insulti, volgarità, contenuti offensivi o discriminatori\n"
                        "4. NON deve essere pubblicità, auto-promozione o vendita di prodotti/servizi\n"
                        "5. NON deve contenere contenuti sessuali, politici o di odio\n"
                        "6. Deve avere un argomento chiaro e comprensibile\n\n"
                        "Sii PERMISSIVO: se la richiesta sembra genuina anche se formulata in modo semplice, approvala. "
                        "Rifiuta solo contenuti chiaramente inappropriati, spam evidente o testo senza senso.\n\n"
                        "Rispondi ESCLUSIVAMENTE con un oggetto JSON (senza markdown, senza backtick) nel formato:\n"
                        '{"approved": true, "reason": "Richiesta approvata"}\n'
                        'oppure {"approved": false, "reason": "motivo del rifiuto in italiano"}'
                    )
                },
                {
                    "role": "user",
                    "content": f"Titolo: {titolo}\nDescrizione: {descrizione}"
                }
            ],
            temperature=0.1,
            max_tokens=200
        )
        
        choice = response.choices[0]
        
        if choice.finish_reason == "content_filter":
            logger.warning("🚫 Validazione: risposta bloccata dal content filter")
            return {"approved": False, "reason": "Il contenuto della richiesta non è stato approvato dal sistema di moderazione."}
        
        result = choice.message.content
        if not result or not result.strip():
            logger.warning("🚫 Validazione: risposta vuota da OpenAI")
            return {"approved": True, "reason": "Richiesta approvata"}  # In dubbio, approva
        
        result = result.strip()
        logger.info(f"📝 Risposta grezza validazione: {result[:200]}")
        
        # Parsing JSON robusto
        validation_result = None
        
        try:
            validation_result = json.loads(result)
        except json.JSONDecodeError:
            pass
        
        if validation_result is None:
            cleaned = result.strip('`').strip()
            if cleaned.startswith('json'):
                cleaned = cleaned[4:].strip()
            try:
                validation_result = json.loads(cleaned)
            except json.JSONDecodeError:
                pass
        
        if validation_result is None:
            import re
            json_match = re.search(r'\{[^{}]*"approved"\s*:\s*(true|false)[^{}]*\}', result, re.IGNORECASE)
            if json_match:
                try:
                    validation_result = json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
        
        if validation_result is None:
            logger.warning(f"⚠️ Validazione: impossibile parsare JSON: {result[:200]}")
            return {"approved": True, "reason": "Richiesta approvata"}  # In dubbio, approva
        
        approved = validation_result.get("approved", True)
        reason = validation_result.get("reason", "Richiesta approvata" if approved else "Richiesta non approvata")
        
        logger.info(f"📝 Validazione richiesta: {'✅ Approvata' if approved else '❌ Rifiutata'} - {reason}")
        return {"approved": approved, "reason": reason}
        
    except Exception as e:
        logger.error(f"❌ Errore validazione richiesta: {e}", exc_info=True)
        # In caso di errore, approva per non bloccare l'utente
        return {"approved": True, "reason": "Richiesta approvata"}


async def controlla_duplicato(titolo: str, descrizione: str, domande_precedenti: list[dict]) -> dict:
    """
    Verifica tramite AI se una nuova richiesta è simile a una già fatta dallo stesso utente.
    
    Args:
        titolo: titolo della nuova richiesta
        descrizione: descrizione della nuova richiesta
        domande_precedenti: lista di dict con {title, description} delle domande precedenti dell'utente
    
    Returns:
        dict con {is_duplicate: bool, reason: str}
    """
    if not domande_precedenti:
        return {"is_duplicate": False, "reason": "Nessuna domanda precedente"}
    
    try:
        client = _get_client()
        
        # Formatta le domande precedenti
        precedenti_text = "\n".join(
            f"- Titolo: {q['title']}\n  Descrizione: {q['description'][:200]}"
            for q in domande_precedenti
        )
        
        logger.info(f"🔍 Controllo duplicato per: '{titolo[:50]}...' vs {len(domande_precedenti)} domande precedenti")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sei un assistente per Ispiramy, una piattaforma italiana di consulenze professionali. "
                        "Devi verificare se una NUOVA richiesta è un duplicato o molto simile a richieste già fatte dallo stesso utente.\n\n"
                        "Una richiesta è considerata DUPLICATA se:\n"
                        "1. Tratta lo STESSO argomento specifico di una richiesta precedente\n"
                        "2. Chiede essenzialmente la STESSA cosa, anche se formulata diversamente\n"
                        "3. È una riformulazione o variazione minima di una domanda già fatta\n\n"
                        "NON è un duplicato se:\n"
                        "1. Tratta un argomento diverso, anche se nella stessa area tematica\n"
                        "2. Chiede qualcosa di specificamente diverso\n"
                        "3. Aggiunge un aspetto nuovo non coperto dalle domande precedenti\n\n"
                        "Rispondi ESCLUSIVAMENTE con un oggetto JSON (senza markdown, senza backtick) nel formato:\n"
                        '{"is_duplicate": true, "reason": "Questa richiesta è simile alla tua domanda precedente: [titolo simile]"}\n'
                        'oppure {"is_duplicate": false, "reason": "Richiesta originale"}'
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"NUOVA RICHIESTA:\nTitolo: {titolo}\nDescrizione: {descrizione}\n\n"
                        f"RICHIESTE PRECEDENTI DELLO STESSO UTENTE:\n{precedenti_text}"
                    )
                }
            ],
            temperature=0.1,
            max_tokens=200
        )
        
        choice = response.choices[0]
        result = choice.message.content
        
        if not result or not result.strip():
            return {"is_duplicate": False, "reason": "Richiesta originale"}
        
        result = result.strip()
        logger.info(f"🔍 Risposta controllo duplicato: {result[:200]}")
        
        # Parsing JSON robusto
        duplicate_result = None
        
        try:
            duplicate_result = json.loads(result)
        except json.JSONDecodeError:
            pass
        
        if duplicate_result is None:
            cleaned = result.strip('`').strip()
            if cleaned.startswith('json'):
                cleaned = cleaned[4:].strip()
            try:
                duplicate_result = json.loads(cleaned)
            except json.JSONDecodeError:
                pass
        
        if duplicate_result is None:
            import re
            json_match = re.search(r'\{[^{}]*"is_duplicate"\s*:\s*(true|false)[^{}]*\}', result, re.IGNORECASE)
            if json_match:
                try:
                    duplicate_result = json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
        
        if duplicate_result is None:
            logger.warning(f"⚠️ Controllo duplicato: impossibile parsare JSON: {result[:200]}")
            return {"is_duplicate": False, "reason": "Richiesta originale"}
        
        is_dup = duplicate_result.get("is_duplicate", False)
        reason = duplicate_result.get("reason", "Richiesta duplicata" if is_dup else "Richiesta originale")
        
        logger.info(f"🔍 Controllo duplicato: {'🔴 Duplicata' if is_dup else '🟢 Originale'} - {reason}")
        return {"is_duplicate": is_dup, "reason": reason}
        
    except Exception as e:
        logger.error(f"❌ Errore controllo duplicato: {e}", exc_info=True)
        return {"is_duplicate": False, "reason": "Richiesta originale"}


async def valida_descrizione_consulenza(descrizione: str) -> dict:
    """
    Valida la descrizione di una consulenza scritta dal cliente.
    Verifica che sia una richiesta sensata e inerente a una consulenza.

    Returns:
        dict con {approved: bool, reason: str}
    """
    try:
        client = _get_client()

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sei un moderatore per Ispiramy, una piattaforma italiana di consulenze professionali. "
                        "Un cliente sta prenotando una consulenza e ha scritto una descrizione di ciò che vuole discutere.\n\n"
                        "Devi verificare che la descrizione:\n"
                        "1. Esprima un argomento o una necessità comprensibile\n"
                        "2. NON sia testo casuale, senza senso, lettere a caso o test\n"
                        "3. NON contenga insulti, volgarità o contenuti offensivi\n"
                        "4. NON sia spam o pubblicità\n"
                        "5. Sia minimamente inerente a una richiesta di consulenza o aiuto professionale\n\n"
                        "Sii PERMISSIVO: se il testo è breve ma ha senso, approvalo. "
                        "Rifiuta solo testo chiaramente privo di significato, offensivo o spam.\n\n"
                        "Rispondi ESCLUSIVAMENTE con un oggetto JSON (senza markdown, senza backtick):\n"
                        '{"approved": true, "reason": "OK"}\n'
                        'oppure {"approved": false, "reason": "motivo del rifiuto in italiano"}'
                    )
                },
                {
                    "role": "user",
                    "content": f"Descrizione consulenza: {descrizione}"
                }
            ],
            temperature=0.1,
            max_tokens=150
        )

        choice = response.choices[0]
        if choice.finish_reason == "content_filter":
            return {"approved": False, "reason": "Il contenuto non è stato approvato dal sistema di moderazione."}

        result = (choice.message.content or "").strip()
        if not result:
            return {"approved": True, "reason": "OK"}

        # Parsing JSON robusto
        validation_result = None
        try:
            validation_result = json.loads(result)
        except json.JSONDecodeError:
            cleaned = result.strip('`').strip()
            if cleaned.startswith('json'):
                cleaned = cleaned[4:].strip()
            try:
                validation_result = json.loads(cleaned)
            except json.JSONDecodeError:
                import re
                m = re.search(r'\{[^{}]*"approved"\s*:\s*(true|false)[^{}]*\}', result, re.IGNORECASE)
                if m:
                    try:
                        validation_result = json.loads(m.group())
                    except json.JSONDecodeError:
                        pass

        if validation_result is None:
            return {"approved": True, "reason": "OK"}

        approved = validation_result.get("approved", True)
        reason = validation_result.get("reason", "OK" if approved else "Descrizione non valida")
        logger.info(f"📝 Validazione descrizione consulenza: {'✅' if approved else '❌'} - {reason}")
        return {"approved": approved, "reason": reason}

    except Exception as e:
        logger.error(f"❌ Errore validazione descrizione consulenza: {e}")
        return {"approved": True, "reason": "OK"}


async def valida_profilo(descrizione: str, professione: str = None, aree_interesse: str = None) -> dict:
    """
    Valida la descrizione del profilo di un consulente tramite AI.
    
    Verifica che la descrizione sia coerente con un professionista che vuole
    offrire consulenze su un determinato argomento:
    1. Descrive competenze, esperienze o servizi professionali reali
    2. Non è testo casuale, senza senso o scritto tanto per riempire il campo
    3. Non contiene contenuti offensivi, inappropriati o spam
    4. È coerente con la professione e le aree di interesse dichiarate
    
    Args:
        descrizione: la descrizione/bio del consulente
        professione: la professione dichiarata (opzionale)
        aree_interesse: le aree di interesse (opzionale)
    
    Returns:
        dict con {approved: bool, reason: str}
    """
    try:
        client = _get_client()
        
        context_parts = [f"Descrizione del profilo:\n{descrizione}"]
        if professione:
            context_parts.append(f"Professione dichiarata: {professione}")
        if aree_interesse:
            context_parts.append(f"Aree di interesse: {aree_interesse}")
        
        user_content = "\n\n".join(context_parts)
        
        logger.info(f"👤 Avvio validazione profilo - Professione: {professione}")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sei un moderatore per Ispiramy, una piattaforma italiana di consulenze professionali. "
                        "I consulenti compilano il proprio profilo con una descrizione per attrarre clienti.\n\n"
                        "Devi verificare che la descrizione del profilo sia GENUINA e PROFESSIONALE:\n"
                        "1. Deve descrivere competenze, esperienze o servizi che il consulente offre\n"
                        "2. NON deve essere testo casuale, senza senso, lorem ipsum o riempitivo\n"
                        "3. NON deve contenere insulti, volgarità o contenuti inappropriati\n"
                        "4. NON deve essere spam o pubblicità di prodotti (va bene promuovere i propri servizi di consulenza)\n"
                        "5. Deve essere coerente con la professione e le aree di interesse dichiarate\n"
                        "6. Deve sembrare scritta da qualcuno che vuole davvero offrire consulenze\n\n"
                        "Sii PERMISSIVO: anche descrizioni semplici o brevi vanno bene se genuine. "
                        "Rifiuta solo testo palesemente finto, casuale o inappropriato.\n\n"
                        "Rispondi ESCLUSIVAMENTE con un oggetto JSON (senza markdown, senza backtick):\n"
                        '{"approved": true, "reason": "Profilo approvato"}\n'
                        'oppure {"approved": false, "reason": "motivo del rifiuto in italiano"}'
                    )
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            temperature=0.1,
            max_tokens=200
        )
        
        choice = response.choices[0]
        
        if choice.finish_reason == "content_filter":
            logger.warning("🚫 Validazione profilo: content filter")
            return {"approved": False, "reason": "Il contenuto del profilo non è stato approvato dal sistema di moderazione."}
        
        result = choice.message.content
        if not result or not result.strip():
            logger.warning("🚫 Validazione profilo: risposta vuota")
            return {"approved": True, "reason": "Profilo approvato"}  # In dubbio, approva
        
        result = result.strip()
        logger.info(f"👤 Risposta grezza validazione profilo: {result[:200]}")
        
        # Parsing JSON robusto
        validation_result = None
        
        try:
            validation_result = json.loads(result)
        except json.JSONDecodeError:
            pass
        
        if validation_result is None:
            cleaned = result.strip('`').strip()
            if cleaned.startswith('json'):
                cleaned = cleaned[4:].strip()
            try:
                validation_result = json.loads(cleaned)
            except json.JSONDecodeError:
                pass
        
        if validation_result is None:
            import re
            json_match = re.search(r'\{[^{}]*"approved"\s*:\s*(true|false)[^{}]*\}', result, re.IGNORECASE)
            if json_match:
                try:
                    validation_result = json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
        
        if validation_result is None:
            logger.warning(f"⚠️ Validazione profilo: impossibile parsare JSON: {result[:200]}")
            return {"approved": True, "reason": "Profilo approvato"}
        
        approved = validation_result.get("approved", True)
        reason = validation_result.get("reason", "Profilo approvato" if approved else "Profilo non approvato")
        
        logger.info(f"👤 Validazione profilo: {'✅ Approvato' if approved else '❌ Rifiutato'} - {reason}")
        return {"approved": approved, "reason": reason}
        
    except Exception as e:
        logger.error(f"❌ Errore validazione profilo: {e}", exc_info=True)
        return {"approved": True, "reason": "Profilo approvato"}
