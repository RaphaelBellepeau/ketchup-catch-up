"""Delete every user from Supabase except a small whitelist.

Use to clean up old throwaway test accounts before a demo. The 2 demo
seed users (Léa Martin, Tom Dupont) are always kept. You can keep extra
phones via argv or the KEEP_PHONES env var (comma-separated).

Usage:
    cd backend
    uv run python scripts/clean_test_users.py
    uv run python scripts/clean_test_users.py +33600000000 +33611112222
    KEEP_PHONES=+33600000000 uv run python scripts/clean_test_users.py

Pass --yes to skip the confirmation prompt.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from supabase import create_client  # noqa: E402

# Demo users seeded by seed_demo_users.py — never delete these.
ALWAYS_KEEP_PHONES = {
    "+33600000001",  # Léa Martin
    "+33600000002",  # Tom Dupont
    "+33600000000",  # dev login (Supabase test phone in .env.development)
}


def normalize(phone: str) -> str:
    """Make the comparison resilient to with/without leading +."""
    p = phone.strip()
    return p if p.startswith("+") else f"+{p}"


def main() -> None:
    url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not service_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in backend/.env")
        sys.exit(1)

    auto_yes = "--yes" in sys.argv
    extra_args = [a for a in sys.argv[1:] if a != "--yes"]
    extra_env = (os.environ.get("KEEP_PHONES") or "").split(",")
    keep_phones = (
        set(map(normalize, ALWAYS_KEEP_PHONES))
        | {normalize(p) for p in extra_args if p}
        | {normalize(p) for p in extra_env if p}
    )

    client = create_client(url, service_key)
    admin = client.auth.admin

    all_users = list(admin.list_users())
    if not all_users:
        print("No users in auth.users. Nothing to do.")
        return

    to_keep = []
    to_delete = []
    for u in all_users:
        phone_raw = getattr(u, "phone", "") or ""
        phone = normalize(phone_raw) if phone_raw else ""
        if phone and phone in keep_phones:
            to_keep.append((u.id, phone))
        else:
            to_delete.append((u.id, phone or "<no phone>"))

    print(f"Total users: {len(all_users)}")
    print(f"\nKeep ({len(to_keep)}):")
    for uid, phone in to_keep:
        print(f"  ✓ {phone}  ({uid})")
    print(f"\nDelete ({len(to_delete)}):")
    for uid, phone in to_delete:
        print(f"  ✗ {phone}  ({uid})")

    if not to_delete:
        print("\nNothing to delete.")
        return

    if not auto_yes:
        print(f"\nThis will delete {len(to_delete)} users from auth.users (cascades).")
        resp = input("Type 'delete' to proceed: ").strip().lower()
        if resp != "delete":
            print("Aborted.")
            return

    deleted = 0
    for uid, phone in to_delete:
        try:
            admin.delete_user(uid)
            deleted += 1
            print(f"  - deleted {phone}")
        except Exception as exc:
            print(f"  ! failed to delete {phone}: {exc}")
    print(f"\nDone. Deleted {deleted}/{len(to_delete)} users.")


if __name__ == "__main__":
    main()
