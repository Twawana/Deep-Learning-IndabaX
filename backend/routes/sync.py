"""
Device ↔ cloud sync endpoints.

Offline app queues changes in SQLite/IndexedDB, then POSTs them here when online.
When Supabase is configured, rows land in PostgreSQL; otherwise we acknowledge
and keep FastAPI local state as the source of truth.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field

from services.supabase_client import (
    FREE_DAILY_PROMPT_LIMIT,
    apply_sync_batch,
    get_daily_usage,
    supabase_configured,
)

router = APIRouter(prefix="/sync", tags=["sync"])


class SyncItem(BaseModel):
    type: str = Field(..., description="farm_profile | chat_message | rangeland_cache")
    payload: dict[str, Any] = Field(default_factory=dict)
    client_id: Optional[str] = None
    created_at: Optional[str] = None


class SyncPushBody(BaseModel):
    device_id: str = Field(..., min_length=1)
    user_id: Optional[str] = None
    items: list[SyncItem] = Field(default_factory=list)


@router.get("/status")
def sync_status() -> dict[str, Any]:
    return {
        "supabase_configured": supabase_configured(),
        "free_daily_prompt_limit": FREE_DAILY_PROMPT_LIMIT,
        "offline_store": "device SQLite / IndexedDB",
        "cloud_store": "Supabase PostgreSQL" if supabase_configured() else "local FastAPI JSON",
    }


@router.post("/push")
def sync_push(
    body: SyncPushBody,
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
) -> dict[str, Any]:
    user_id = body.user_id or x_user_id
    result = apply_sync_batch(
        user_id=user_id,
        device_id=body.device_id,
        items=[item.model_dump() for item in body.items],
    )
    return result


@router.get("/usage/{user_id}")
def sync_usage(user_id: str) -> dict[str, Any]:
    usage = get_daily_usage(user_id)
    return {
        **usage,
        "remaining": max(0, int(usage.get("limit") or FREE_DAILY_PROMPT_LIMIT) - int(usage.get("count") or 0)),
    }
