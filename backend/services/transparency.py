"""
Data transparency helpers for AI-facing tool outputs.

Tracks missing fields, stale observations, and confidence — never pretends data is perfect.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Iterable, Optional

# Observations older than this are flagged as potentially outdated for advisory use.
STALE_DAYS = 180


def _as_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none"}:
        return None
    try:
        return datetime.fromisoformat(text[:10]).date()
    except ValueError:
        return None


def observation_age_days(observation_date: Any, *, today: Optional[date] = None) -> Optional[int]:
    obs = _as_date(observation_date)
    if obs is None:
        return None
    ref = today or datetime.now(timezone.utc).date()
    return (ref - obs).days


def is_stale(observation_date: Any, *, max_age_days: int = STALE_DAYS) -> bool:
    age = observation_age_days(observation_date)
    return age is not None and age > max_age_days


def missing_field_limitations(
    payload: dict[str, Any],
    required_labels: dict[str, str],
) -> list[str]:
    """
    Build human-readable limitation strings for missing keys.

    required_labels maps field_key -> limitation message when missing/None.
    """
    limitations: list[str] = []
    for key, message in required_labels.items():
        value = payload.get(key)
        if value is None or value == "" or value == []:
            limitations.append(message)
    return limitations


def confidence_from_limitations(
    limitations: Iterable[str],
    *,
    high_max: int = 0,
    medium_max: int = 2,
) -> str:
    """
    Map limitation count to confidence.
    high: no material gaps; medium: some gaps; low: many gaps or critical missing data.
    """
    count = len(list(limitations))
    if count <= high_max:
        return "high"
    if count <= medium_max:
        return "medium"
    return "low"


def merge_limitations(*groups: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for group in groups:
        for item in group:
            text = str(item).strip()
            if text and text not in seen:
                seen.add(text)
                ordered.append(text)
    return ordered
