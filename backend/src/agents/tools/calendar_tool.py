"""Calendar availability for negotiation agents.

If the user has connected Google Calendar (we have a refresh token), pull
real free/busy slots in the meet-up window. Otherwise return an empty list
— the agent then relies on the weekly_summary memory ("yoga Tue/Thu evenings",
etc.) to decide what's free.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Iterable
from zoneinfo import ZoneInfo

from src.services import gcal_client

logger = logging.getLogger(__name__)

# Hackathon hardcode — most demo users live in Europe/Paris. When we add
# per-user TZ to the profile we'll wire that in here.
LOCAL_TZ = ZoneInfo("Europe/Paris")


async def get_busy_for_window(
    user_id: str,
    time_min: datetime,
    time_max: datetime,
) -> list[dict]:
    """Return [{start, end}] busy windows or [] if calendar not connected.

    `time_min` and `time_max` MUST be timezone-aware. We pad `time_max` by
    one calendar day so a "12 May → 12 May" window actually covers the
    full 24h of 12 May (Google's freeBusy is exclusive on the upper bound).
    """
    try:
        connected = await gcal_client.is_connected(user_id)
    except Exception:
        connected = False
    if not connected:
        return []

    if time_min.tzinfo is None:
        time_min = time_min.replace(tzinfo=LOCAL_TZ)
    if time_max.tzinfo is None:
        time_max = time_max.replace(tzinfo=LOCAL_TZ)
    # Google freeBusy: timeMax is exclusive — extend by 1 day so the
    # user's chosen end day is fully covered.
    query_max = time_max + timedelta(days=1)

    try:
        busy = await gcal_client.get_busy_slots(user_id, time_min, query_max)
        logger.info(
            "Calendar busy fetched user=%s window=%s→%s count=%d",
            user_id, time_min.isoformat(), query_max.isoformat(), len(busy),
        )
        return busy
    except Exception:
        logger.exception("Calendar read failed for user=%s", user_id)
        return []


def _parse_iso(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_window(time_window: str) -> tuple[datetime, datetime]:
    """Decode the catchup `time_window` value into (from_dt, until_dt) with
    `Europe/Paris` timezone applied so downstream callers (Google freeBusy,
    Calendar event POST) get RFC3339 strings with a real offset.

    Front-end stores it as ``"<iso_from>|<iso_until>"`` — usually bare
    YYYY-MM-DD dates. If parsing fails we fall back to "now → now+14
    days" so the agents always have a grounded window to reason about.
    """
    parts = (time_window or "").split("|")
    if len(parts) == 2:
        a, b = _parse_iso(parts[0]), _parse_iso(parts[1])
        if a and b and a <= b:
            if a.tzinfo is None:
                a = a.replace(tzinfo=LOCAL_TZ)
            if b.tzinfo is None:
                b = b.replace(tzinfo=LOCAL_TZ)
            return a, b
    now = datetime.now(LOCAL_TZ)
    return now, now + timedelta(days=14)


def format_calendar_view(
    busy: list[dict],
    window_from: datetime,
    window_until: datetime,
) -> str:
    """Render the meet-up window day-by-day with weekday labels and any
    busy slots, so the LLM never has to compute "what weekday is
    2026-05-23".

    ``busy`` is a list of ``{start, end}`` ISO strings (Google Calendar
    free/busy shape). When empty, every day shows "Free".
    """
    if window_from > window_until:
        return "(invalid window)"

    by_day: dict[str, list[tuple[str, str]]] = {}
    for b in busy or []:
        s_dt = _parse_iso(b.get("start", ""))
        e_dt = _parse_iso(b.get("end", ""))
        if not s_dt or not e_dt:
            continue
        key = s_dt.strftime("%Y-%m-%d")
        by_day.setdefault(key, []).append(
            (s_dt.strftime("%H:%M"), e_dt.strftime("%H:%M"))
        )

    lines: list[str] = []
    cur: date = window_from.date()
    end_d: date = window_until.date()
    # Soft cap so the prompt doesn't explode on giant windows.
    max_days = 21
    days_emitted = 0
    while cur <= end_d and days_emitted < max_days:
        key = cur.strftime("%Y-%m-%d")
        slots = sorted(by_day.get(key, []))
        weekday = cur.strftime("%a %d %b")
        if slots:
            slots_text = ", ".join(f"busy {s}–{e}" for s, e in slots)
            lines.append(f"  {weekday} · {slots_text}")
        else:
            lines.append(f"  {weekday} · Free")
        cur += timedelta(days=1)
        days_emitted += 1
    if cur <= end_d:
        lines.append(f"  … (window continues to {end_d.strftime('%a %d %b')})")
    return "\n".join(lines)


def fmt_window_bounds(values: Iterable[str | datetime]) -> str:
    """Best-effort 'Thu 1 May' style formatter for prompt strings."""
    out: list[str] = []
    for v in values:
        if isinstance(v, datetime):
            out.append(v.strftime("%a %d %b"))
        else:
            out.append(str(v))
    return " → ".join(out)
