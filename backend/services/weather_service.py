"""
Open-Meteo weather client (no API key required).
"""

from __future__ import annotations

import os
from typing import Any, Optional

import requests

DEFAULT_BASE_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_FORECAST_DAYS = 7


class WeatherServiceError(Exception):
    """Raised when the weather provider cannot be reached or returns bad data."""

    def __init__(self, message: str, *, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _base_url() -> str:
    return os.getenv("OPEN_METEO_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def _timeout() -> float:
    raw = os.getenv("OPEN_METEO_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
    try:
        return float(raw)
    except ValueError:
        return float(DEFAULT_TIMEOUT_SECONDS)


def fetch_forecast(
    latitude: float,
    longitude: float,
    *,
    forecast_days: int = DEFAULT_FORECAST_DAYS,
    past_days: int = 7,
) -> dict[str, Any]:
    """
    Fetch recent + forecast daily rainfall/temperature for a coordinate.

    Uses Open-Meteo `past_days` + `forecast_days` (no invented values).
    Returns normalized dict with `recent_daily` and `forecast_daily` split on today.
    """
    from datetime import date

    days = max(1, min(int(forecast_days), 16))
    history = max(0, min(int(past_days), 92))
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ",".join(
            [
                "precipitation_sum",
                "precipitation_probability_max",
                "temperature_2m_max",
                "temperature_2m_min",
            ]
        ),
        "timezone": "Africa/Windhoek",
        "forecast_days": days,
        "past_days": history,
    }

    try:
        response = requests.get(_base_url(), params=params, timeout=_timeout())
    except requests.Timeout as exc:
        raise WeatherServiceError("Open-Meteo request timed out.") from exc
    except requests.RequestException as exc:
        raise WeatherServiceError(f"Open-Meteo request failed: {exc}") from exc

    if response.status_code >= 400:
        raise WeatherServiceError(
            f"Open-Meteo returned HTTP {response.status_code}.",
            status_code=response.status_code,
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise WeatherServiceError("Open-Meteo returned invalid JSON.") from exc

    daily = payload.get("daily") or {}
    dates = daily.get("time") or []
    precip = daily.get("precipitation_sum") or []
    precip_prob = daily.get("precipitation_probability_max") or []
    temp_max = daily.get("temperature_2m_max") or []
    temp_min = daily.get("temperature_2m_min") or []

    rows: list[dict[str, Any]] = []
    for i, day in enumerate(dates):
        rows.append(
            {
                "date": day,
                "precipitation_mm": _safe_float(precip[i] if i < len(precip) else None),
                "precipitation_probability_max": _safe_float(
                    precip_prob[i] if i < len(precip_prob) else None
                ),
                "temperature_max_c": _safe_float(temp_max[i] if i < len(temp_max) else None),
                "temperature_min_c": _safe_float(temp_min[i] if i < len(temp_min) else None),
            }
        )

    today = date.today().isoformat()
    recent_daily = [r for r in rows if r["date"] < today]
    forecast_daily = [r for r in rows if r["date"] >= today]

    def _total(daily_rows: list[dict[str, Any]]) -> Optional[float]:
        values = [r["precipitation_mm"] for r in daily_rows if r["precipitation_mm"] is not None]
        return round(sum(values), 2) if values else None

    return {
        "latitude": payload.get("latitude", latitude),
        "longitude": payload.get("longitude", longitude),
        "timezone": payload.get("timezone", "Africa/Windhoek"),
        "forecast_days": days,
        "past_days": history,
        "recent_daily": recent_daily,
        "forecast_daily": forecast_daily,
        "total_recent_precipitation_mm": _total(recent_daily),
        "total_forecast_precipitation_mm": _total(forecast_daily),
        "source": "open-meteo",
    }


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
