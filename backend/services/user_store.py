"""
User persistence for Farmar auth/admin.

Prefer Supabase `users` table when configured; fall back to the users list
embedded in local admin_state.json.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any, Optional

from services import supabase_client

DEFAULT_USERS = [
    {
        "id": "user-main",
        "name": "Farm User",
        "username": "farmer",
        "email": "farmer@farmar.local",
        "password": "farmer123",
        "role": "user",
        "status": "active",
        "tier": "free",
        "ai_usage": 0,
        "last_login": None,
    },
    {
        "id": "admin-main",
        "name": "Admin",
        "username": "admin",
        "email": "admin@farmar.local",
        "password": "admin123",
        "role": "admin",
        "status": "active",
        "tier": "premium",
        "ai_usage": 0,
        "last_login": None,
    },
]


def use_supabase_users() -> bool:
    mode = (os.getenv("AUTH_SOURCE") or os.getenv("DATA_SOURCE") or "auto").strip().lower()
    if mode in {"csv", "local", "file", "json"}:
        return False
    if mode in {"supabase", "remote"}:
        return supabase_client.is_configured()
    return supabase_client.is_configured()


def hash_password(password: str) -> str:
    return hashlib.sha256(str(password).encode("utf-8")).hexdigest()


def verify_password(password: str, stored: str | None) -> bool:
    if stored is None:
        return False
    stored_s = str(stored)
    if not stored_s:
        return False
    plain = str(password)
    if stored_s == plain:
        return True
    if stored_s == hash_password(plain):
        return True
    return False


def _row_to_user(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id")),
        "name": row.get("name") or "",
        "username": (row.get("username") or "").strip().lower(),
        "email": (row.get("email") or "").strip().lower(),
        "password": row.get("password_hash") or row.get("password") or "",
        "role": row.get("role") or "user",
        "status": row.get("status") or "active",
        "tier": row.get("tier") or "free",
        "ai_usage": int(row.get("ai_usage") or 0),
        "last_login": row.get("last_login"),
    }


def _user_to_row(user: dict[str, Any], *, for_insert: bool = False) -> dict[str, Any]:
    password = user.get("password") or ""
    # If already sha256 hex, keep; otherwise hash plaintext
    if len(password) == 64 and all(c in "0123456789abcdef" for c in password.lower()):
        password_hash = password
    elif password:
        password_hash = hash_password(password)
    else:
        password_hash = None

    row: dict[str, Any] = {
        "name": user.get("name"),
        "username": (user.get("username") or "").strip().lower(),
        "email": (user.get("email") or "").strip().lower(),
        "password_hash": password_hash,
        "role": user.get("role") or "user",
        "status": user.get("status") or "active",
        "tier": user.get("tier") or "free",
        "ai_usage": int(user.get("ai_usage") or 0),
        "last_login": user.get("last_login"),
    }
    # Only send id on insert when it's a non-UUID demo id that Postgres may reject.
    # Prefer letting Supabase generate UUIDs unless id looks like a UUID.
    user_id = str(user.get("id") or "")
    if for_insert and _looks_like_uuid(user_id):
        row["id"] = user_id
    elif not for_insert and user_id:
        row["id"] = user_id
    return row


def _looks_like_uuid(value: str) -> bool:
    parts = value.split("-")
    return len(parts) == 5 and len(value) == 36


def list_users() -> list[dict[str, Any]]:
    rows = supabase_client.fetch_all("users")
    return [_row_to_user(row) for row in rows]


def ensure_default_users() -> list[dict[str, Any]]:
    """Insert demo farmer/admin accounts if missing (by username)."""
    users = list_users()
    by_username = {u["username"]: u for u in users if u.get("username")}
    created = False
    for template in DEFAULT_USERS:
        if template["username"] in by_username:
            continue
        payload = _user_to_row(
            {
                **template,
                "password": template["password"],
            },
            for_insert=True,
        )
        # Drop null password_hash key if empty
        payload = {k: v for k, v in payload.items() if v is not None}
        inserted = supabase_client.insert_rows("users", [payload])
        if inserted:
            users.append(_row_to_user(inserted[0]))
            created = True
    return users if created else list_users()


def _friendly_db_error(exc: Exception) -> str:
    text = str(exc)
    lower = text.lower()
    if "23505" in lower or "duplicate" in lower or "unique" in lower:
        if "email" in lower:
            return "That email is already registered. Try logging in."
        if "username" in lower:
            return "That username is already taken. Choose another."
        return "An account with those details already exists. Try logging in."
    if "supabase" in lower and "not configured" in lower:
        return "Account database is not configured on the server."
    return text


def create_user(user: dict[str, Any]) -> dict[str, Any]:
    payload = {k: v for k, v in _user_to_row(user, for_insert=True).items() if v is not None}
    now = _utc_now()
    payload.setdefault("created_at", now)
    payload.setdefault("updated_at", now)
    try:
        inserted = supabase_client.insert_rows("users", [payload])
    except supabase_client.SupabaseError as exc:
        raise supabase_client.SupabaseError(_friendly_db_error(exc)) from exc
    if not inserted:
        raise supabase_client.SupabaseError("Failed to create user in the account database.")
    return _row_to_user(inserted[0])


def update_user(user_id: str, values: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key in ("name", "username", "email", "role", "status", "tier", "ai_usage", "last_login"):
        if key in values and values[key] is not None:
            payload[key] = values[key]
    if "password" in values and values["password"] is not None:
        payload["password_hash"] = (
            values["password"]
            if len(str(values["password"])) == 64
            else hash_password(str(values["password"]))
        )
    payload["updated_at"] = _utc_now()
    try:
        updated = supabase_client.update_rows(
            "users",
            match={"id": user_id},
            values=payload,
        )
    except supabase_client.SupabaseError as exc:
        raise supabase_client.SupabaseError(_friendly_db_error(exc)) from exc
    if not updated:
        raise supabase_client.SupabaseError(f"User not found: {user_id}")
    return _row_to_user(updated[0])


def delete_user(user_id: str) -> None:
    supabase_client.delete_rows("users", match={"id": user_id})


def find_user(
    users: list[dict[str, Any]], identifier: str
) -> Optional[dict[str, Any]]:
    needle = identifier.strip().lower()
    for user in users:
        if user.get("email", "").lower() == needle or user.get("username", "").lower() == needle:
            return user
    return None


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
