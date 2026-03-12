# Helpy — Copilot Instructions

## Project Overview
Helpy is an Italian-language professional consultation marketplace built with **FastAPI + SQLModel + Jinja2 server-rendered templates**. It connects clients with consultants via bookings, video calls (Agora.io), Stripe payments, and community Q&A. The codebase uses Italian for all UI text, comments, variable names, and user-facing strings.

## Architecture & Key Files
- **Entry point**: `app/main.py` — FastAPI app, middleware setup, route registration, startup/shutdown hooks
- **All DB models**: `app/models.py` — single file with every SQLModel table (User, Booking, Conversation, Message, CommunityQuestion, etc.)
- **DB engine & session**: `app/database.py` — dual-DB support (SQLite dev / PostgreSQL prod via `DATABASE_URL` env var)
- **Routes**: `app/routes/` — each file is a FastAPI `APIRouter`; pattern is HTML page `GET` + JSON API `POST`/`GET` endpoints
- **Utils/services**: `app/utils/` — Agora, Stripe, email, notifications
- **Templates**: `app/templates/` — Jinja2 HTML; `base.html` is the shared layout with navbar + chat widget
- **Scheduler**: `app/scheduler.py` — APScheduler for automatic booking reminders (1h and 10min before)

## Critical Patterns

### Database Sessions
Two patterns coexist — use the **context manager** from `database.py` for route handlers:
```python
from app.database import get_session
with get_session() as session:
    user = session.get(User, user_id)
```
Some files (e.g., `stripe_webhook.py`, `scheduler.py`) use direct `Session(engine)` — match whichever pattern the file already uses.

### Authentication
Always authenticate via `verify_token(request)` from `app/routes/auth.py`. It returns `Optional[User]` (detached from session). For HTML pages, redirect to login; for API endpoints, return 401:
```python
from app.routes.auth import verify_token
user = verify_token(request)
if not user:
    return RedirectResponse("/login", status_code=302)  # HTML pages
    # or: raise HTTPException(status_code=401)           # API endpoints
```

### Notification System
Two notification modules exist — use the one matching the importing file's convention:
- `app/utils/notification_service.py` — `send_notification(user_id, type_key, title, message, ...)` — used by `booking.py`, `stripe_webhook.py`, `scheduler.py`
- `app/utils/notification_manager.py` — `send_notification(notification_type_key, recipient_user_id, recipient_email, ...)` — used by `messages.py`
Both check `notification_types` DB table for in-app/email flags before sending.

### Conversation Normalization
Conversations always store `user1_id < user2_id`. Use `get_or_create_conversation(session, user1_id, user2_id)` from `messages.py` which handles the ordering.

### Category Hierarchy
Categories use a many-to-many self-referencing structure: `Category` table + `CategoryHierarchy` (parent → child). Filter principal categories with `Category.is_principal == True`. Subcategories stored on User as JSON string in `selected_subcategories`.

## Development Workflow
```bash
# Run locally (auto-creates SQLite DB on startup)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# Run with Docker
docker compose up --build

# Run tests
pytest -v
```
The app auto-creates all tables on startup via `SQLModel.metadata.create_all()` in `database.py`.

## Database Migrations
No Alembic — migrations are **manual SQL files** in `sql_update/`. Each migration has separate SQLite and PostgreSQL variants (suffix `_postgres.sql`). When adding a new column or table, create both variants.

## Conventions
- **Logging**: Use `from app.logger_config import logger` (Loguru), not stdlib `logging`. Some files import `from loguru import logger` directly — both work.
- **Route files**: Create router with `router = APIRouter()`, include in `main.py` with `app.include_router()`
- **Templates**: Render via `request.app.state.templates.TemplateResponse("name.html", {"request": request, ...})`
- **Timezone**: Use `ZoneInfo("Europe/Rome")` for all datetime operations (Italian timezone)
- **User display**: Use `get_display_name(user)` from `utils_user.py` — respects anonymous mode
- **Passwords**: Hashed with MD5 via `hash_md5()` in `utils_user.py`
- **External services** (Stripe, Agora, S3, SendGrid): All configured via environment variables, gracefully degrade if credentials are missing
