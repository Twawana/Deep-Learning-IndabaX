"""
Admin and auth routes for frontend account management.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/admin", tags=["admin"])

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
STATE_PATH = DATA_DIR / "admin_state.json"
ADMIN_PASSCODE = "indaba-admin"

DEFAULT_USERS = [
    {
        "id": "user-main",
        "name": "Farm User",
        "email": "farmer@farmar.local",
        "role": "user",
        "status": "active",
        "last_login": None,
    },
    {
        "id": "admin-main",
        "name": "Admin",
        "email": "admin@farmar.local",
        "role": "admin",
        "status": "active",
        "last_login": None,
    },
]

DEFAULT_STATE = {
    "current_user_id": "user-main",
    "users": DEFAULT_USERS,
    "app_settings": {"maintenance_mode": False, "allow_data_sync": True},
}


class LoginBody(BaseModel):
    passcode: str = Field(..., min_length=1)


class SwitchBody(BaseModel):
    user_id: str = Field(..., min_length=1)


class AddUserBody(BaseModel):
    name: str = Field(..., min_length=1)
    email: str | None = None
    role: Literal["user", "admin"] = "user"


class UpdateUserBody(BaseModel):
    role: Literal["user", "admin"] | None = None
    status: Literal["active", "disabled"] | None = None


class UpdateSettingsBody(BaseModel):
    maintenance_mode: bool | None = None
    allow_data_sync: bool | None = None


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


def _normalize_state(raw: dict[str, Any]) -> dict[str, Any]:
    users = raw.get("users") or DEFAULT_USERS
    state = {
        "current_user_id": raw.get("current_user_id") or "user-main",
        "users": users,
        "app_settings": {
            **DEFAULT_STATE["app_settings"],
            **(raw.get("app_settings") or {}),
        },
    }
    if not any(user.get("id") == state["current_user_id"] for user in users):
        state["current_user_id"] = users[0]["id"]
    return state


def _state_response(state: dict[str, Any], message: str | None = None) -> dict[str, Any]:
    current = next(
        (u for u in state["users"] if u["id"] == state["current_user_id"]),
        state["users"][0],
    )
    return {
        "current_user": current,
        "is_admin": current.get("role") == "admin",
        "users": state["users"],
        "app_settings": state["app_settings"],
        "message": message,
    }


@router.get("/state", summary="Fetch auth/admin state")
def admin_state() -> dict[str, Any]:
    state = _normalize_state(_load_state())
    return _state_response(state)


@router.post("/login", summary="Login as admin")
def admin_login(body: LoginBody) -> dict[str, Any]:
    if body.passcode.strip() != ADMIN_PASSCODE:
        raise HTTPException(status_code=401, detail="Invalid admin passcode.")
    state = _normalize_state(_load_state())
    state["current_user_id"] = "admin-main"
    state = _save_state(state)
    return _state_response(state, "Logged in as admin.")


@router.post("/switch", summary="Switch active account")
def switch_user(body: SwitchBody) -> dict[str, Any]:
    state = _normalize_state(_load_state())
    user = next((u for u in state["users"] if u["id"] == body.user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.get("status") != "active":
        raise HTTPException(status_code=400, detail="User is not active.")
    state["current_user_id"] = body.user_id
    state = _save_state(state)
    return _state_response(state, "Account switched.")


@router.post("/logout", summary="Logout to default user")
def logout_user() -> dict[str, Any]:
    state = _normalize_state(_load_state())
    state["current_user_id"] = "user-main"
    state = _save_state(state)
    return _state_response(state, "Logged out.")


@router.post("/users", summary="Add user")
def add_user(body: AddUserBody) -> dict[str, Any]:
    state = _normalize_state(_load_state())
    clean = body.name.strip()
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
            "email": (body.email or f"{user_id}@farmar.local").strip(),
            "role": body.role,
            "status": "active",
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
    if state["current_user_id"] == user_id:
        state["current_user_id"] = users[0]["id"]
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
