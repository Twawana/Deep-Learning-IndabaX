"""
Admin and auth routes for frontend account management.

Uses per-browser session tokens (X-Session-Token) so multiple clients
can stay logged in independently. Global current_user_id is no longer used
as the source of truth for "who is logged in".
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import APIRouter, Header, HTTPException
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
    "current_user_id": None,  # legacy; kept for file compatibility
    "sessions": {},  # token -> user_id
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
    # Demo payment stub — never send/store full card numbers.
    payment: Optional[dict[str, Any]] = None


def _validate_premium_payment(payment: Optional[dict[str, Any]]) -> Optional[str]:
    """Lightweight demo checks so Premium is not a one-click free switch."""
    if not isinstance(payment, dict):
        return "Card payment details are required to upgrade to Premium."
    last4 = str(payment.get("last4") or "").strip()
    name = str(payment.get("cardholder_name") or "").strip()
    brand = str(payment.get("brand") or "").strip()
    if len(last4) != 4 or not last4.isdigit():
        return "Invalid card details (last4)."
    if len(name) < 2:
        return "Cardholder name is required."
    if not brand:
        return "Card brand is required."
    for key in ("card_number", "number", "cvc", "cvv"):
        if payment.get(key):
            return "Do not send full card numbers to the server."
    return None


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
        return dict(DEFAULT_STATE)
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return dict(DEFAULT_STATE)


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
    sessions = {
        str(token): str(uid)
        for token, uid in (raw.get("sessions") or {}).items()
        if token and uid
    }
    # Drop sessions pointing at missing users
    valid_ids = {u["id"] for u in users}
    sessions = {t: uid for t, uid in sessions.items() if uid in valid_ids}
    return {
        "current_user_id": None,
        "sessions": sessions,
        "users": users,
        "app_settings": {
            **DEFAULT_STATE["app_settings"],
            **(raw.get("app_settings") or {}),
        },
    }


def _user_for_token(state: dict[str, Any], token: Optional[str]) -> dict[str, Any] | None:
    if not token:
        return None
    user_id = (state.get("sessions") or {}).get(token)
    if not user_id:
        return None
    return next((u for u in state["users"] if u["id"] == user_id), None)


def _issue_session(state: dict[str, Any], user_id: str) -> str:
    token = secrets.token_urlsafe(24)
    sessions = dict(state.get("sessions") or {})
    sessions[token] = user_id
    # Cap sessions per user to avoid unbounded growth
    owned = [t for t, uid in sessions.items() if uid == user_id]
    if len(owned) > 8:
        for old in owned[:-8]:
            sessions.pop(old, None)
    state["sessions"] = sessions
    return token


def _state_response(
    state: dict[str, Any],
    *,
    message: str | None = None,
    session_token: str | None = None,
    current_user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current_raw = current_user
    current = _public_user(current_raw) if current_raw else GUEST_USER
    is_admin = current.get("role") == "admin"
    payload = {
        "current_user": current,
        "is_logged_in": current_raw is not None,
        "is_admin": is_admin,
        "users": [_public_user(user) for user in state["users"]] if is_admin else [],
        "app_settings": state["app_settings"],
        "message": message,
    }
    if session_token:
        payload["session_token"] = session_token
    return payload


def _require_user(
    state: dict[str, Any],
    x_session_token: Optional[str],
) -> dict[str, Any]:
    user = _user_for_token(state, x_session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Please log in first.")
    if user.get("status") != "active":
        raise HTTPException(status_code=400, detail="This account is disabled.")
    return user


def _find_user(state: dict[str, Any], identifier: str) -> dict[str, Any] | None:
    needle = identifier.strip().lower()
    for user in state["users"]:
        if user.get("email", "").lower() == needle or user.get("username", "").lower() == needle:
            return user
    return None


@router.get("/state", summary="Fetch auth/admin state for this browser session")
def admin_state(
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
) -> dict[str, Any]:
    state = _normalize_state(_load_state())
    user = _user_for_token(state, x_session_token)
    return _state_response(state, current_user=user)


@router.post("/login", summary="Login with email/username and password")
def login(body: CredentialLoginBody) -> dict[str, Any]:
    state = _normalize_state(_load_state())
    user = _find_user(state, body.identifier)
    if not user or user.get("password") != body.password:
        raise HTTPException(status_code=401, detail="Invalid email/username or password.")
    if user.get("status") != "active":
        raise HTTPException(status_code=400, detail="This account is disabled.")
    user["last_login"] = _now()
    token = _issue_session(state, user["id"])
    state = _save_state(state)
    return _state_response(
        state,
        message=f"Logged in as {user['name']}.",
        session_token=token,
        current_user=user,
    )


@router.post("/register", summary="Create a new free account")
def register(body: RegisterBody) -> dict[str, Any]:
    state = _normalize_state(_load_state())
    email = body.email.strip().lower()
    username = (body.username or email.split("@")[0]).strip().lower()
    name = body.name.strip()
    password = body.password

    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    if len(password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters.")
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Please enter your name.")
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
    token = _issue_session(state, user_id)
    state = _save_state(state)
    return _state_response(
        state,
        message=f"Account created. Welcome, {name}!",
        session_token=token,
        current_user=new_user,
    )


@router.post("/logout", summary="Logout this browser session")
def logout_user(
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
) -> dict[str, Any]:
    state = _normalize_state(_load_state())
    if x_session_token and x_session_token in (state.get("sessions") or {}):
        state["sessions"].pop(x_session_token, None)
        state = _save_state(state)
    return _state_response(state, message="Logged out.", current_user=None)


@router.post("/upgrade", summary="Upgrade or change subscription for current user")
def upgrade_subscription(
    body: UpgradeBody,
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
) -> dict[str, Any]:
    state = _normalize_state(_load_state())
    current = _require_user(state, x_session_token)

    payment_meta: Optional[dict[str, Any]] = None
    if body.tier == "premium":
        err = _validate_premium_payment(body.payment)
        if err:
            raise HTTPException(status_code=400, detail=err)
        assert body.payment is not None
        payment_meta = {
            "last4": str(body.payment.get("last4")),
            "brand": str(body.payment.get("brand")),
            "cardholder_name": str(body.payment.get("cardholder_name")),
            "billing_country": body.payment.get("billing_country"),
            "amount_label": body.payment.get("amount_label") or "N$89 per month",
            "demo": True,
            "paid_at": _now(),
        }

    for user in state["users"]:
        if user["id"] != current["id"]:
            continue
        user["tier"] = body.tier
        if body.tier == "premium" and payment_meta:
            user["subscription"] = {
                "plan": "premium",
                "status": "active",
                "payment": payment_meta,
            }
        elif body.tier == "free":
            user["subscription"] = {"plan": "free", "status": "cancelled"}
        current = user
        break
    state = _save_state(state)
    if body.tier == "premium":
        last4 = (payment_meta or {}).get("last4", "****")
        message = f"Payment successful. Premium unlocked (card ending {last4})."
    else:
        message = "Subscription updated to Free."
    return _state_response(
        state,
        message=message,
        current_user=current,
    )


@router.post("/ai-usage", summary="Record one AI Ask usage for current user")
def record_ai_usage(
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
) -> dict[str, Any]:
    state = _normalize_state(_load_state())
    current = _user_for_token(state, x_session_token)
    if not current:
        return _state_response(state, message="Guest usage not tracked.", current_user=None)
    for user in state["users"]:
        if user["id"] == current["id"]:
            user["ai_usage"] = int(user.get("ai_usage") or 0) + 1
            current = user
            break
    state = _save_state(state)
    return _state_response(state, message="AI usage recorded.", current_user=current)


@router.post("/users", summary="Add user")
def add_user(
    body: AddUserBody,
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
) -> dict[str, Any]:
    state = _normalize_state(_load_state())
    actor = _require_user(state, x_session_token)
    if actor.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
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
    return _state_response(state, message=f"{clean} added.", current_user=actor)


@router.patch("/users/{user_id}", summary="Update user")
def update_user(
    user_id: str,
    body: UpdateUserBody,
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
) -> dict[str, Any]:
    state = _normalize_state(_load_state())
    actor = _require_user(state, x_session_token)
    if actor.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
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
    return _state_response(state, message="User updated.", current_user=actor)


@router.delete("/users/{user_id}", summary="Remove user")
def delete_user(
    user_id: str,
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
) -> dict[str, Any]:
    if user_id == "admin-main":
        raise HTTPException(status_code=400, detail="Default admin cannot be removed.")
    state = _normalize_state(_load_state())
    actor = _require_user(state, x_session_token)
    if actor.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    users = [user for user in state["users"] if user["id"] != user_id]
    if len(users) == len(state["users"]):
        raise HTTPException(status_code=404, detail="User not found.")
    state["users"] = users
    state["sessions"] = {
        t: uid for t, uid in (state.get("sessions") or {}).items() if uid != user_id
    }
    state = _save_state(state)
    return _state_response(state, message="User removed.", current_user=actor)


@router.patch("/settings", summary="Update app settings")
def update_settings(
    body: UpdateSettingsBody,
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
) -> dict[str, Any]:
    state = _normalize_state(_load_state())
    actor = _require_user(state, x_session_token)
    if actor.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    if body.maintenance_mode is not None:
        state["app_settings"]["maintenance_mode"] = body.maintenance_mode
    if body.allow_data_sync is not None:
        state["app_settings"]["allow_data_sync"] = body.allow_data_sync
    state = _save_state(state)
    return _state_response(state, message="Settings updated.", current_user=actor)
