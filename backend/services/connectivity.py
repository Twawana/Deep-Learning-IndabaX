"""Network / mode helpers shared by weather tools and the Vision agent."""

from __future__ import annotations

import os
import socket


def is_online(timeout_seconds: float = 2.0) -> bool:
    """
    Lightweight connectivity check for Gemini / Open-Meteo.

    VISION_FORCE_MODE=offline|local forces offline; online forces online.
    """
    force = (os.getenv("VISION_FORCE_MODE") or "").strip().lower()
    if force in {"offline", "local"}:
        return False
    if force in {"online"}:
        return True

    hosts = (
        ("generativelanguage.googleapis.com", 443),
        ("api.open-meteo.com", 443),
        ("1.1.1.1", 443),
    )
    for host, port in hosts:
        try:
            with socket.create_connection((host, port), timeout=timeout_seconds):
                return True
        except OSError:
            continue
    return False
