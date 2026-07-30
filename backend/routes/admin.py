"""
Admin and auth routes for frontend account management.

Uses per-browser session tokens (X-Session-Token) so multiple clients
can stay logged in independently. Global current_user_id is no longer used
as the source of truth for "who is logged in".

Users prefer Supabase `users` when configured; sessions + app_settings stay
in local admin_state.json.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from services import user_store
from services.supabase_client import SupabaseError

router = APIRouter(prefix="/admin", tags=["admin"])

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
STATE_PATH = DATA_DIR / "admin_state.json"

DEFAULT_USERS = user_store.DEFAULT_USERS

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


def _load_local_raw() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return dict(DEFAULT_STATE)
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return dict(DEFAULT_STATE)


def _save_local(state: dict[str, Any]) -> dict[str, Any]:
    """Persist sessions + settings locally. Users are omitted when using Supabase."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "current_user_id": None,
        "sessions": state.get("sessions") or {},
        "app_settings": state.get("app_settings") or DEFAULT_STATE["app_settings"],
    }
    if not user_store.use_supabase_users():
        payload["users"] = state.get("users") or DEFAULT_USERS
    STATE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return state


def _load_users_from_sources(local_users: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if user_store.use_supabase_users():
        try:
            return [
                _normalize_user(user) for user in user_store.ensure_default_users()
            ]
        except SupabaseError:
            # Keep API usable if Supabase is briefly down
            return [_normalize_user(user) for user in (local_users or DEFAULT_USERS)]
    return [_normalize_user(user) for user in (local_users or DEFAULT_USERS)]


def _load_state() -> dict[str, Any]:
    return _load_local_raw()


def _save_state(state: dict[str, Any]) -> dict[str, Any]:
    return _save_local(state)


def _normalize_user(user: dict[str, Any]) -> dict[str, Any]:
    defaults = next(
        (item for item in DEFAULT_USERS if item["id"] == user.get("id")),
        None,
    )
    username = (
        user.get("username")
        or (defaults or {}).get("username")
        or ""
    ).strip().lower()
    email = (
        user.get("email")
        or (defaults or {}).get("email")
        or ""
    ).strip().lower()
    password = user.get("password")
    if not password and defaults:
        password = defaults.get("password") or ""
    password = password or ""
    return {
        **user,
        "username": username or (email.split("@")[0] if email else "user"),
        "email": email,
        "password": password,
        "tier": user.get("tier")
        if user.get("tier") in {"free", "premium"}
        else ("premium" if user.get("role") == "admin" else "free"),
        "ai_usage": int(user.get("ai_usage") or 0),
    }


def _normalize_state(raw: dict[str, Any]) -> dict[str, Any]:
    users = _load_users_from_sources(raw.get("users") or DEFAULT_USERS)
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
    return user_store.find_user(state["users"], identifier)


def _persist_user_fields(user: dict[str, Any], fields: dict[str, Any]) -> dict[str, Any]:
    """Write user field updates to Supabase when enabled; else mutate local state object."""
    if user_store.use_supabase_users():
        try:
            return _normalize_user(user_store.update_user(str(user["id"]), fields))
        except SupabaseError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
    user.update(fields)
    return user


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
    if not user or not user_store.verify_password(body.password, user.get("password")):
        raise HTTPException(status_code=401, detail="Invalid email/username or password.")
    if user.get("status") != "active":
        raise HTTPException(status_code=400, detail="This account is disabled.")
    updated = _persist_user_fields(user, {"last_login": _now()})
    # Refresh list entry
    state["users"] = [
        updated if u["id"] == updated["id"] else u for u in state["users"]
    ]
    token = _issue_session(state, updated["id"])
    state = _save_state(state)
    return _state_response(
        state,
        message=f"Logged in as {updated['name']}.",
        session_token=token,
        current_user=updated,
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

    if user_store.use_supabase_users():
        try:
            new_user = _normalize_user(
                user_store.create_user(
                    {
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
                )
            )
        except SupabaseError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        state["users"].append(new_user)
        saved_where = "account database"
    else:
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
        saved_where = "local server"

    token = _issue_session(state, new_user["id"])
    state = _save_state(state)
    return _state_response(
        state,
        message=f"Account created and saved to the {saved_where}. Welcome, {name}!",
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
    # Also persist tier to user store / Supabase when available
    try:
        current = _persist_user_fields(current, {"tier": body.tier})
        state["users"] = [
            current if u["id"] == current["id"] else u for u in state["users"]
        ]
    except Exception:
        pass
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
    updated = _persist_user_fields(
        current, {"ai_usage": int(current.get("ai_usage") or 0) + 1}
    )
    state["users"] = [
        updated if u["id"] == updated["id"] else u for u in state["users"]
    ]
    state = _save_state(state)
    return _state_response(state, message="AI usage recorded.", current_user=updated)


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

    if user_store.use_supabase_users():
        try:
            created = _normalize_user(
                user_store.create_user(
                    {
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
            )
        except SupabaseError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        state["users"].append(created)
    else:
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
    target = next((u for u in state["users"] if u["id"] == user_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    fields: dict[str, Any] = {}
    if body.role is not None:
        fields["role"] = body.role
    if body.status is not None:
        fields["status"] = body.status
    if body.tier is not None:
        fields["tier"] = body.tier
    updated = _persist_user_fields(target, fields) if fields else target
    state["users"] = [
        updated if u["id"] == updated["id"] else u for u in state["users"]
    ]
    state = _save_state(state)
    return _state_response(state, message="User updated.", current_user=actor)


@router.delete("/users/{user_id}", summary="Remove user")
def delete_user(
    user_id: str,
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
) -> dict[str, Any]:
    if user_id in {"admin-main"}:
        raise HTTPException(status_code=400, detail="Default admin cannot be removed.")
    state = _normalize_state(_load_state())
    actor = _require_user(state, x_session_token)
    if actor.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    target = next((u for u in state["users"] if u["id"] == user_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    if target.get("username") == "admin":
        raise HTTPException(status_code=400, detail="Default admin cannot be removed.")

    if user_store.use_supabase_users():
        try:
            user_store.delete_user(user_id)
        except SupabaseError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    users = [user for user in state["users"] if user["id"] != user_id]
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
