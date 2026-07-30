"""
Admin and auth routes for frontend account management.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/admin", tags=["admin"])

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
STATE_PATH = DATA_DIR / "admin_state.json"

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

DEFAULT_STATE = {
    "current_user_id": None,
    "users": DEFAULT_USERS,
    "app_settings": {"maintenance_mode": False, "allow_data_sync": True},
}

GUEST_USER = {
    "id": "guest",
    "name": "Guest",
    "username": "guest",
    "email": "",
    "role": "guest",
    "status": "active",
    "tier": "free",
    "ai_usage": 0,
    "last_login": None,
}


class CredentialLoginBody(BaseModel):
    identifier: str = Field(..., min_length=1, description="Email or username")
    password: str = Field(..., min_length=1)


class RegisterBody(BaseModel):
    name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=3)
    username: str | None = None
    password: str = Field(..., min_length=4)


class AddUserBody(BaseModel):
    name: str = Field(..., min_length=1)
    email: str | None = None
    username: str | None = None
    password: str = Field(default="changeme", min_length=1)
    role: Literal["user", "admin"] = "user"
    tier: Literal["free", "premium"] = "free"


class UpdateUserBody(BaseModel):
    role: Literal["user", "admin"] | None = None
    status: Literal["active", "disabled"] | None = None
    tier: Literal["free", "premium"] | None = None


class UpdateSettingsBody(BaseModel):
    maintenance_mode: bool | None = None
    allow_data_sync: bool | None = None


class UpgradeBody(BaseModel):
    tier: Literal["free", "premium"] = "premium"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user.get("id"),
        "name": user.get("name"),
        "username": user.get("username"),
        "email": user.get("email"),
        "role": user.get("role"),
        "status": user.get("status"),
        "tier": user.get("tier"),
        "ai_usage": int(user.get("ai_usage") or 0),
        "last_login": user.get("last_login"),
    }


def _load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return DEFAULT_STATE
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_STATE


def _save_state(state: dict[str, Any]) -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state


def _normalize_user(user: dict[str, Any]) -> dict[str, Any]:
    defaults = next(
        (item for item in DEFAULT_USERS if item["id"] == user.get("id")),
        DEFAULT_USERS[0],
    )
    username = (user.get("username") or defaults.get("username") or "").strip().lower()
    email = (user.get("email") or defaults.get("email") or "").strip().lower()
    password = user.get("password") or defaults.get("password") or "changeme"
    return {
        **user,
        "username": username or email.split("@")[0],
        "email": email,
        "password": password,
        "tier": user.get("tier")
        if user.get("tier") in {"free", "premium"}
        else ("premium" if user.get("role") == "admin" else "free"),
        "ai_usage": int(user.get("ai_usage") or 0),
    }


def _normalize_state(raw: dict[str, Any]) -> dict[str, Any]:
    users = [_normalize_user(user) for user in (raw.get("users") or DEFAULT_USERS)]
    current_id = raw.get("current_user_id")
    if current_id and not any(user.get("id") == current_id for user in users):
        current_id = None
    return {
        "current_user_id": current_id,
        "users": users,
        "app_settings": {
            **DEFAULT_STATE["app_settings"],
            **(raw.get("app_settings") or {}),
        },
    }


def _state_response(state: dict[str, Any], message: str | None = None) -> dict[str, Any]:
    current_raw = next(
        (u for u in state["users"] if u["id"] == state.get("current_user_id")),
        None,
    )
    current = _public_user(current_raw) if current_raw else GUEST_USER
    return {
        "current_user": current,
        "is_logged_in": current_raw is not None,
        "is_admin": current.get("role") == "admin",
        "users": [_public_user(user) for user in state["users"]],
        "app_settings": state["app_settings"],
        "message": message,
    }


def _find_user(state: dict[str, Any], identifier: str) -> dict[str, Any] | None:
    needle = identifier.strip().lower()
    for user in state["users"]:
        if user.get("email", "").lower() == needle or user.get("username", "").lower() == needle:
            return user
    return None


@router.get("/state", summary="Fetch auth/admin state")
def admin_state() -> dict[str, Any]:
    state = _normalize_state(_load_state())
    return _state_response(state)


@router.post("/login", summary="Login with email/username and password")
def login(body: CredentialLoginBody) -> dict[str, Any]:
    state = _normalize_state(_load_state())
    user = _find_user(state, body.identifier)
    if not user or user.get("password") != body.password:
        raise HTTPException(status_code=401, detail="Invalid email/username or password.")
    if user.get("status") != "active":
        raise HTTPException(status_code=400, detail="This account is disabled.")
    user["last_login"] = _now()
    state["current_user_id"] = user["id"]
    state = _save_state(state)
    return _state_response(state, f"Logged in as {user['name']}.")


@router.post("/register", summary="Create a new free account")
def register(body: RegisterBody) -> dict[str, Any]:
    state = _normalize_state(_load_state())
    email = body.email.strip().lower()
    username = (body.username or email.split("@")[0]).strip().lower()
    name = body.name.strip()
    password = body.password

    if "@" not in email:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    if len(password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters.")
    if _find_user(state, email) or _find_user(state, username):
        raise HTTPException(status_code=400, detail="Email or username already exists.")

    user_id = (
        "user-"
        + "".join(ch if ch.isalnum() else "-" for ch in username).strip("-")
        + "-"
        + str(len(state["users"]) + 1)
    )
    new_user = {
        "id": user_id,
        "name": name,
        "username": username,
        "email": email,
        "password": password,
        "role": "user",
        "status": "active",
        "tier": "free",
        "ai_usage": 0,
        "last_login": _now(),
    }
    state["users"].append(new_user)
    state["current_user_id"] = user_id
    state = _save_state(state)
    return _state_response(state, f"Account created. Welcome, {name}!")


@router.post("/logout", summary="Logout")
def logout_user() -> dict[str, Any]:
    state = _normalize_state(_load_state())
    state["current_user_id"] = None
    state = _save_state(state)
    return _state_response(state, "Logged out.")


@router.post("/upgrade", summary="Upgrade or change subscription for current user")
def upgrade_subscription(body: UpgradeBody) -> dict[str, Any]:
    state = _normalize_state(_load_state())
    current_id = state.get("current_user_id")
    if not current_id:
        raise HTTPException(status_code=401, detail="Please log in to manage your subscription.")
    updated = False
    for user in state["users"]:
        if user["id"] != current_id:
            continue
        user["tier"] = body.tier
        updated = True
        break
    if not updated:
        raise HTTPException(status_code=404, detail="User not found.")
    state = _save_state(state)
    label = "Premium" if body.tier == "premium" else "Free"
    return _state_response(state, f"Subscription updated to {label}.")


@router.post("/ai-usage", summary="Record one AI Ask usage for current user")
def record_ai_usage() -> dict[str, Any]:
    state = _normalize_state(_load_state())
    current_id = state.get("current_user_id")
    if not current_id:
        return _state_response(state, "Guest usage not tracked.")
    for user in state["users"]:
        if user["id"] == current_id:
            user["ai_usage"] = int(user.get("ai_usage") or 0) + 1
            break
    state = _save_state(state)
    return _state_response(state, "AI usage recorded.")


@router.post("/users", summary="Add user")
def add_user(body: AddUserBody) -> dict[str, Any]:
    state = _normalize_state(_load_state())
    clean = body.name.strip()
    email = (body.email or f"{clean.lower().replace(' ', '.')}@farmar.local").strip().lower()
    username = (body.username or email.split("@")[0]).strip().lower()
    if _find_user(state, email) or _find_user(state, username):
        raise HTTPException(status_code=400, detail="Email or username already exists.")
    user_id = (
        "user-"
        + "".join(ch if ch.isalnum() else "-" for ch in clean.lower()).strip("-")
        + "-"
        + str(len(state["users"]) + 1)
    )
    state["users"].append(
        {
            "id": user_id,
            "name": clean,
            "username": username,
            "email": email,
            "password": body.password,
            "role": body.role,
            "status": "active",
            "tier": body.tier,
            "ai_usage": 0,
            "last_login": None,
        }
    )
    state = _save_state(state)
    return _state_response(state, f"{clean} added.")


@router.patch("/users/{user_id}", summary="Update user")
def update_user(user_id: str, body: UpdateUserBody) -> dict[str, Any]:
    state = _normalize_state(_load_state())
    updated = False
    for user in state["users"]:
        if user["id"] != user_id:
            continue
        if body.role is not None:
            user["role"] = body.role
        if body.status is not None:
            user["status"] = body.status
        if body.tier is not None:
            user["tier"] = body.tier
        updated = True
        break
    if not updated:
        raise HTTPException(status_code=404, detail="User not found.")
    state = _save_state(state)
    return _state_response(state, "User updated.")


@router.delete("/users/{user_id}", summary="Remove user")
def delete_user(user_id: str) -> dict[str, Any]:
    if user_id == "admin-main":
        raise HTTPException(status_code=400, detail="Default admin cannot be removed.")
    state = _normalize_state(_load_state())
    users = [user for user in state["users"] if user["id"] != user_id]
    if len(users) == len(state["users"]):
        raise HTTPException(status_code=404, detail="User not found.")
    state["users"] = users
    if state.get("current_user_id") == user_id:
        state["current_user_id"] = None
    state = _save_state(state)
    return _state_response(state, "User removed.")


@router.patch("/settings", summary="Update app settings")
def update_settings(body: UpdateSettingsBody) -> dict[str, Any]:
    state = _normalize_state(_load_state())
    if body.maintenance_mode is not None:
        state["app_settings"]["maintenance_mode"] = body.maintenance_mode
    if body.allow_data_sync is not None:
        state["app_settings"]["allow_data_sync"] = body.allow_data_sync
    state = _save_state(state)
    return _state_response(state, "Settings updated.")
