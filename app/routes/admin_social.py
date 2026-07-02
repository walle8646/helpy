"""
Routes admin per la gestione dei contenuti social (bozze, approvazione, pubblicazione).
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlmodel import Session, select
from datetime import datetime
from zoneinfo import ZoneInfo
from pydantic import BaseModel
from typing import Optional

from app.database import engine
from app.models import SocialDraft
from app.routes.admin import require_admin
from app.logger_config import logger

router = APIRouter(prefix="/admin")

ITALY_TZ = ZoneInfo("Europe/Rome")

PLATFORM_LABELS = {
    "facebook": "Facebook",
    "instagram": "Instagram",
    "tiktok": "TikTok",
}


@router.get("/social", response_class=HTMLResponse)
async def admin_social(request: Request):
    """Dashboard social: bozze generate, approvazione e pubblicazione."""
    admin_user = require_admin(request)
    if not admin_user:
        return RedirectResponse("/login", status_code=302)

    with Session(engine) as session:
        drafts = session.exec(
            select(SocialDraft).order_by(SocialDraft.created_at.desc()).limit(200)
        ).all()

    counts = {}
    for d in drafts:
        counts[d.status] = counts.get(d.status, 0) + 1

    # Stato account collegati (best effort, non bloccare la pagina se l'API è giù)
    accounts = {}
    try:
        from app.social.publisher import get_connected_accounts
        accounts = get_connected_accounts()
    except Exception as e:
        logger.warning(f"Admin social: impossibile leggere account Post for Me: {e}")

    return request.app.state.templates.TemplateResponse("admin/social.html", {
        "request": request,
        "user": admin_user,
        "current_user": admin_user,
        "drafts": drafts,
        "counts": counts,
        "accounts": accounts,
        "platform_labels": PLATFORM_LABELS,
    })


class GenerateRequest(BaseModel):
    limit: int = 3


@router.post("/social/generate")
async def admin_social_generate(data: GenerateRequest, request: Request):
    """Genera nuove bozze dalle top domande community (chiama GPT, può richiedere qualche secondo)."""
    admin_user = require_admin(request)
    if not admin_user:
        return JSONResponse({"ok": False, "message": "Non autorizzato"}, status_code=403)

    try:
        from app.social.content_generator import generate_batch, save_packages_as_drafts
        limit = max(1, min(data.limit, 10))
        packages = generate_batch(limit)
        created = save_packages_as_drafts(packages)
        return {"ok": True, "message": f"Creati {created} draft da {len(packages)} domande"}
    except Exception as e:
        logger.error(f"Admin social: errore generazione: {e}", exc_info=True)
        return JSONResponse({"ok": False, "message": str(e)[:300]}, status_code=500)


class DraftUpdateRequest(BaseModel):
    caption: Optional[str] = None
    media_urls: Optional[str] = None
    scheduled_at: Optional[str] = None  # "YYYY-MM-DDTHH:MM" ora italiana, "" per azzerare


@router.post("/social/drafts/{draft_id}")
async def admin_social_update_draft(draft_id: int, data: DraftUpdateRequest, request: Request):
    """Aggiorna testo, media o programmazione di un draft."""
    admin_user = require_admin(request)
    if not admin_user:
        return JSONResponse({"ok": False, "message": "Non autorizzato"}, status_code=403)

    with Session(engine) as session:
        draft = session.get(SocialDraft, draft_id)
        if not draft:
            return JSONResponse({"ok": False, "message": "Draft non trovato"}, status_code=404)
        if draft.status in ("published", "publishing"):
            return JSONResponse({"ok": False, "message": "Draft già pubblicato/in pubblicazione"}, status_code=400)

        if data.caption is not None:
            draft.caption = data.caption[:5000]
        if data.media_urls is not None:
            draft.media_urls = data.media_urls.strip()[:3000] or None
        if data.scheduled_at is not None:
            if data.scheduled_at.strip():
                try:
                    draft.scheduled_at = datetime.fromisoformat(data.scheduled_at.strip())
                except ValueError:
                    return JSONResponse({"ok": False, "message": "Formato data non valido"}, status_code=400)
            else:
                draft.scheduled_at = None
        draft.updated_at = datetime.utcnow()
        session.add(draft)
        session.commit()
    return {"ok": True, "message": "Draft aggiornato"}


@router.post("/social/drafts/{draft_id}/status")
async def admin_social_draft_status(draft_id: int, request: Request):
    """Cambia stato del draft: body {"action": "approve"|"reject"|"back_to_draft"}."""
    admin_user = require_admin(request)
    if not admin_user:
        return JSONResponse({"ok": False, "message": "Non autorizzato"}, status_code=403)

    body = await request.json()
    action = body.get("action")
    transitions = {
        "approve": ("draft", "failed"),   # da questi stati si può approvare
        "reject": ("draft", "approved"),
        "back_to_draft": ("approved", "rejected", "failed"),
    }
    new_status = {"approve": "approved", "reject": "rejected", "back_to_draft": "draft"}.get(action)
    if not new_status:
        return JSONResponse({"ok": False, "message": "Azione non valida"}, status_code=400)

    with Session(engine) as session:
        draft = session.get(SocialDraft, draft_id)
        if not draft:
            return JSONResponse({"ok": False, "message": "Draft non trovato"}, status_code=404)
        if draft.status not in transitions[action]:
            return JSONResponse({"ok": False, "message": f"Transizione non permessa da '{draft.status}'"}, status_code=400)
        draft.status = new_status
        if action == "approve":
            draft.error = None
        draft.updated_at = datetime.utcnow()
        session.add(draft)
        session.commit()
    return {"ok": True, "message": f"Stato: {new_status}"}


@router.post("/social/drafts/{draft_id}/publish")
async def admin_social_publish_now(draft_id: int, request: Request):
    """Pubblica subito un draft approvato (o ritenta un failed dopo verifica idempotente)."""
    admin_user = require_admin(request)
    if not admin_user:
        return JSONResponse({"ok": False, "message": "Non autorizzato"}, status_code=403)

    from app.social.publisher import publish_draft
    result = publish_draft(draft_id)
    status_code = 200 if result["ok"] else 400
    return JSONResponse(result, status_code=status_code)


@router.post("/social/refresh-results")
async def admin_social_refresh_results(request: Request):
    """Forza l'aggiornamento degli esiti dei post in pubblicazione."""
    admin_user = require_admin(request)
    if not admin_user:
        return JSONResponse({"ok": False, "message": "Non autorizzato"}, status_code=403)

    from app.social.publisher import check_publishing_results
    check_publishing_results()
    return {"ok": True, "message": "Esiti aggiornati"}


@router.delete("/social/drafts/{draft_id}")
async def admin_social_delete_draft(draft_id: int, request: Request):
    """Elimina un draft (solo se non pubblicato)."""
    admin_user = require_admin(request)
    if not admin_user:
        return JSONResponse({"ok": False, "message": "Non autorizzato"}, status_code=403)

    with Session(engine) as session:
        draft = session.get(SocialDraft, draft_id)
        if not draft:
            return JSONResponse({"ok": False, "message": "Draft non trovato"}, status_code=404)
        if draft.status in ("published", "publishing"):
            return JSONResponse({"ok": False, "message": "Non eliminabile: già pubblicato/in pubblicazione"}, status_code=400)
        session.delete(draft)
        session.commit()
    return {"ok": True, "message": "Draft eliminato"}
