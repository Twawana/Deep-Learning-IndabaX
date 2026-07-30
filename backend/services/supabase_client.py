"""
Optional Supabase (PostgreSQL) client for Farmar cloud data.

When SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY are set, the backend can
persist users, chat, usage, and farm profiles in Postgres.
Otherwise the app keeps using local JSON / device offline storage.
"""

from __future__ import annotations

import logging
import os
from datetime import date, datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

FREE_DAILY_PROMPT_LIMIT = int(os.getenv("FREE_DAILY_PROMPT_LIMIT", "10"))


def supabase_configured() -> bool:
    return bool(
        os.getenv("SUPABASE_URL", "").strip()
        and os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    )


def get_supabase_client():
    if not supabase_configured():
        return None
    try:
        from supabase import create_client
    except ImportError:
        logger.warning("supabase package not installed; cloud DB disabled.")
        return None
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    return create_client(url, key)


def upsert_farm_profile(user_id: str, farm: dict[str, Any]) -> bool:
    client = get_supabase_client()
    if not client or not user_id:
        return False
    row = {
        "user_id": user_id,
        "farmer_name": farm.get("farmerName") or farm.get("farmer_name"),
        "farm_name": farm.get("farmName") or farm.get("farm_name"),
        "location": farm.get("location"),
        "herd_size": farm.get("herdSize") or farm.get("herd_size"),
        "livestock_type": farm.get("livestockType") or farm.get("livestock_type"),
        "farm_size_ha": farm.get("farmSizeHa") or farm.get("farm_size_ha"),
        "land_tenure": farm.get("landTenure") or farm.get("land_tenure"),
        "payload": farm,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        client.table("farm_profiles").upsert(row, on_conflict="user_id").execute()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Supabase farm upsert failed: %s", exc)
        return False


def insert_chat_message(
    *,
    user_id: Optional[str],
    role: str,
    content: str,
    location: Optional[str] = None,
    agent: Optional[str] = None,
    mode: Optional[str] = None,
    tools_used: Any = None,
    decision: Any = None,
) -> bool:
    client = get_supabase_client()
    if not client:
        return False
    row = {
        "user_id": user_id,
        "role": role,
        "content": content,
        "location": location,
        "agent": agent,
        "mode": mode,
        "tools_used": tools_used,
        "decision": decision,
    }
    try:
        client.table("chat_messages").insert(row).execute()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Supabase chat insert failed: %s", exc)
        return False


def increment_daily_usage(user_id: str) -> dict[str, Any]:
    """
    Increment today's prompt count. Returns {count, limit, allowed}.
    Premium callers should skip the limit check at a higher layer.
    """
    client = get_supabase_client()
    today = date.today().isoformat()
    limit = FREE_DAILY_PROMPT_LIMIT
    if not client or not user_id:
        return {"count": 0, "limit": limit, "allowed": True, "cloud": False}

    try:
        existing = (
            client.table("usage_daily")
            .select("prompt_count")
            .eq("user_id", user_id)
            .eq("usage_date", today)
            .limit(1)
            .execute()
        )
        rows = existing.data or []
        count = int(rows[0]["prompt_count"]) if rows else 0
        count += 1
        client.table("usage_daily").upsert(
            {
                "user_id": user_id,
                "usage_date": today,
                "prompt_count": count,
            },
            on_conflict="user_id,usage_date",
        ).execute()
        client.table("profiles").update({"ai_usage_total": count}).eq(
            "id", user_id
        ).execute()
        return {
            "count": count,
            "limit": limit,
            "allowed": count <= limit,
            "cloud": True,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Supabase usage increment failed: %s", exc)
        return {"count": 0, "limit": limit, "allowed": True, "cloud": False}


def get_daily_usage(user_id: str) -> dict[str, Any]:
    client = get_supabase_client()
    limit = FREE_DAILY_PROMPT_LIMIT
    today = date.today().isoformat()
    if not client or not user_id:
        return {"count": 0, "limit": limit, "cloud": False}
    try:
        existing = (
            client.table("usage_daily")
            .select("prompt_count")
            .eq("user_id", user_id)
            .eq("usage_date", today)
            .limit(1)
            .execute()
        )
        rows = existing.data or []
        count = int(rows[0]["prompt_count"]) if rows else 0
        return {"count": count, "limit": limit, "cloud": True}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Supabase usage read failed: %s", exc)
        return {"count": 0, "limit": limit, "cloud": False}


def upsert_rangeland_cache(location_key: str, payload: dict[str, Any]) -> bool:
    client = get_supabase_client()
    if not client or not location_key:
        return False
    try:
        client.table("rangeland_cache").upsert(
            {
                "location_key": location_key,
                "payload": payload,
                "source": payload.get("source") or "dataset",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="location_key",
        ).execute()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Supabase rangeland cache failed: %s", exc)
        return False


def apply_sync_batch(user_id: Optional[str], device_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply offline→cloud sync queue items from a device."""
    client = get_supabase_client()
    applied = 0
    errors: list[str] = []
    if not client:
        return {
            "ok": False,
            "applied": 0,
            "message": "Supabase not configured — sync kept on device only.",
            "errors": errors,
        }

    for item in items or []:
        kind = (item.get("type") or item.get("event_type") or "").strip()
        payload = item.get("payload") or {}
        try:
            if kind == "farm_profile" and user_id:
                upsert_farm_profile(user_id, payload)
            elif kind == "chat_message" and user_id:
                insert_chat_message(
                    user_id=user_id,
                    role=payload.get("role") or "user",
                    content=payload.get("content") or "",
                    location=payload.get("location"),
                    agent=payload.get("agent"),
                    mode=payload.get("mode"),
                    tools_used=payload.get("tools_used"),
                    decision=payload.get("decision"),
                )
            elif kind == "rangeland_cache":
                upsert_rangeland_cache(
                    payload.get("location_key") or payload.get("location") or "",
                    payload.get("data") or payload,
                )
            client.table("sync_events").insert(
                {
                    "user_id": user_id,
                    "device_id": device_id,
                    "event_type": kind or "unknown",
                    "payload": payload,
                }
            ).execute()
            applied += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{kind}: {exc}")

    return {
        "ok": not errors,
        "applied": applied,
        "message": f"Synced {applied} item(s) to Supabase.",
        "errors": errors,
    }
