"""
CLI per generare bozze di contenuti social dalle domande della community.

Uso (dentro al container web):
    docker compose exec web python scripts/generate_social_content.py --limit 5
    docker compose exec web python scripts/generate_social_content.py --limit 10 --out /app/social_drafts.json

Output: stampa un riepilogo leggibile + (opzionale) salva JSON completo.
"""
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.social.content_generator import generate_batch  # noqa: E402


def print_draft(d: dict) -> None:
    c = d.get("content", {})
    ig = c.get("instagram", {})
    tt = c.get("tiktok", {})
    li = c.get("linkedin", {})
    print("\n" + "=" * 70)
    print(f"📌 DOMANDA #{d['source_question_id']} [{d['category']}] "
          f"(👍 {d['engagement']['upvotes']} · 👁 {d['engagement']['views']})")
    print(f"   {d['source_title']}")
    print("-" * 70)
    print("📷 INSTAGRAM")
    print(f"   Hook: {ig.get('hook', '—')}")
    slides = ig.get("carousel_slides", [])
    for i, s in enumerate(slides, 1):
        print(f"   Slide {i}: {s}")
    print(f"   Caption: {ig.get('caption', '—')}")
    print(f"   Hashtag: {' '.join(ig.get('hashtags', []))}")
    print("-" * 70)
    print("🎵 TIKTOK")
    print(f"   Hook: {tt.get('hook', '—')}")
    print(f"   Script: {tt.get('script', '—')}")
    print(f"   Hashtag: {' '.join(tt.get('hashtags', []))}")
    print("-" * 70)
    print("💼 LINKEDIN")
    print(f"   {li.get('post', '—')}")
    print(f"   Hashtag: {' '.join(li.get('hashtags', []))}")
    print("-" * 70)
    print(f"🎯 CTA: {c.get('cta', '—')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera bozze social dalla community")
    parser.add_argument("--limit", type=int, default=5, help="Numero di domande da elaborare")
    parser.add_argument("--out", type=str, help="Path file JSON di output (opzionale)")
    args = parser.parse_args()

    print(f"🚀 Genero contenuti social per le top {args.limit} domande community...")
    drafts = generate_batch(args.limit)

    if not drafts:
        print("\n⚠️ Nessuna bozza generata. Il DB ha domande community validate?")
        print("   (Se il DB locale è vuoto, fai prima il clone da prod o seed di domande)")
        sys.exit(0)

    for d in drafts:
        print_draft(d)

    if args.out:
        Path(args.out).write_text(json.dumps(drafts, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n💾 Salvate {len(drafts)} bozze in {args.out}")

    print(f"\n✅ Generate {len(drafts)} bozze.")


if __name__ == "__main__":
    main()
