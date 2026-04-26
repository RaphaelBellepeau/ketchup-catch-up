"""Seed two demo users for the hackathon demo.

These users are pre-onboarded so they show up in /users/discoverable and can
be added to a fresh user's first group, letting the agent negotiation flow
have something realistic to chew on.

Idempotent: running this twice is safe. Existing users are detected by phone
and just get their memories refreshed.

Usage:
    cd backend
    uv run python scripts/seed_demo_users.py
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running from backend/ directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from supabase import create_client  # noqa: E402

DEMO_USERS = [
    {
        "phone": "+33600000001",
        "name": "Léa Martin",
        "memories": [
            ("location_summary", "Lives in the 11th arrondissement of Paris, near Bastille."),
            ("weekly_summary", "Has a yoga class every Tuesday and Thursday evening 7-9pm; otherwise free weeknights."),
            ("personality_summary", "Prefers cozy small dinners with 3-4 close friends — quiet bistros over loud bars."),
        ],
    },
    {
        "phone": "+33600000002",
        "name": "Tom Dupont",
        "memories": [
            ("location_summary", "Lives in Montmartre, north Paris."),
            ("weekly_summary", "Plays football every Wednesday night and crashes early on Sundays."),
            ("personality_summary", "Loves loud lively places — natural wine bars, late dinners, dancing afterwards."),
        ],
    },
]


def main() -> None:
    url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not service_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in backend/.env")
        sys.exit(1)

    client = create_client(url, service_key)
    now_iso = datetime.now(timezone.utc).isoformat()

    for spec in DEMO_USERS:
        phone = spec["phone"]
        name = spec["name"]
        print(f"\n— {name} ({phone})")

        # 1. Find or create the auth user.
        user_id = _ensure_auth_user(client, phone, name)
        if not user_id:
            print(f"  ! could not find or create auth user — skipping")
            continue

        # 2. Patch the public.users row created by the on_auth_user_created
        #    trigger so the name + onboarded_at are filled in.
        client.table("users").update(
            {"name": name, "onboarded_at": now_iso}
        ).eq("id", user_id).execute()
        print(f"  ✓ public.users updated (id={user_id})")

        # 3. Replace the demo memories so seed re-runs stay clean.
        client.table("memories").delete().eq("user_id", user_id).eq(
            "source", "demo_seed"
        ).execute()
        rows = [
            {
                "user_id": user_id,
                "scope": scope,
                "content": content,
                "source": "demo_seed",
            }
            for scope, content in spec["memories"]
        ]
        client.table("memories").insert(rows).execute()
        print(f"  ✓ {len(rows)} memories seeded")

    print("\nDone.")


def _ensure_auth_user(client, phone: str, name: str) -> str | None:
    """Find an existing auth.users row by phone, or create one. Returns the
    user id (uuid) or None on failure.
    """
    # supabase-py exposes admin API as client.auth.admin
    admin = client.auth.admin
    try:
        # list_users iterates over all auth users — fine for hackathon scale.
        existing = admin.list_users()
        for u in existing:
            if getattr(u, "phone", None) == phone.lstrip("+"):
                print(f"  ✓ auth user already exists (id={u.id})")
                return u.id
    except Exception as exc:
        print(f"  ! list_users failed: {exc}")

    # Not found → create. phone_confirm bypasses the OTP step.
    try:
        result = admin.create_user(
            {
                "phone": phone,
                "phone_confirm": True,
                "user_metadata": {"name": name, "demo_seed": True},
            }
        )
        # supabase-py wraps in `result.user`
        user = getattr(result, "user", None) or result
        user_id = getattr(user, "id", None)
        if not user_id:
            print(f"  ! create_user returned no id: {result!r}")
            return None
        print(f"  ✓ auth user created (id={user_id})")
        return user_id
    except Exception as exc:
        print(f"  ! create_user failed: {exc}")
        return None


if __name__ == "__main__":
    main()
