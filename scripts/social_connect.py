"""Collega gli account social a Post for Me (postforme.dev).

Uso:
    python scripts/social_connect.py            # genera i link OAuth da aprire nel browser
    python scripts/social_connect.py --status   # mostra gli account collegati

La API key viene letta da .env (POSTFORME_API_KEY).
"""
import sys
import json
import urllib.request
from pathlib import Path

API_BASE = "https://api.postforme.dev/v1"
PLATFORMS = ["facebook", "instagram", "tiktok"]


def load_api_key() -> str:
    for line in (Path(__file__).parent.parent / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("POSTFORME_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("POSTFORME_API_KEY non trovata nel .env")


def api(method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        method=method,
        headers={
            "Authorization": f"Bearer {load_api_key()}",
            "Content-Type": "application/json",
        },
        data=json.dumps(body).encode() if body else None,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def show_status() -> None:
    accounts = api("GET", "/social-accounts").get("data", [])
    if not accounts:
        print("Nessun account collegato.")
        return
    print(f"Account collegati: {len(accounts)}\n")
    for a in accounts:
        print(f"  [{a.get('platform')}] {a.get('username') or a.get('name') or a.get('id')}"
              f"  (status: {a.get('status', '?')}, id: {a.get('id')})")


def generate_auth_urls() -> None:
    print("Apri questi link nel browser e fai login con l'account Ispiramy:\n")
    for platform in PLATFORMS:
        result = api("POST", "/social-accounts/auth-url", {
            "platform": platform,
            "external_id": f"ispiramy-{platform}",
            "permissions": ["posts", "feeds"],
        })
        print(f"  {platform.upper()}:\n  {result['url']}\n")
    print("Dopo aver collegato tutti gli account, verifica con:")
    print("    python scripts/social_connect.py --status")


if __name__ == "__main__":
    if "--status" in sys.argv:
        show_status()
    else:
        generate_auth_urls()
