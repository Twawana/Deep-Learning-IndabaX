"""
Open-Meteo weather client (no API key required).

- Forecast endpoint: near-term forecast + recent past_days
- Archive endpoint: cross-check / prefer for completed past days (better historical fidelity)
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

import requests

DEFAULT_BASE_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_FORECAST_DAYS = 7
NAMIBIA_TZ = ZoneInfo("Africa/Windhoek")


class WeatherServiceError(Exception):
    """Raised when the weather provider cannot be reached or returns bad data."""

    def __init__(self, message: str, *, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _base_url() -> str:
    return os.getenv("OPEN_METEO_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def _archive_url() -> str:
    return os.getenv("OPEN_METEO_ARCHIVE_URL", DEFAULT_ARCHIVE_URL).rstrip("/")


def _timeout() -> float:
    raw = os.getenv("OPEN_METEO_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
    try:
        return float(raw)
    except ValueError:
        return float(DEFAULT_TIMEOUT_SECONDS)


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _request_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        response = requests.get(url, params=params, timeout=_timeout())
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
        return response.json()
    except ValueError as exc:
        raise WeatherServiceError("Open-Meteo returned invalid JSON.") from exc


def _rows_from_daily(daily: dict[str, Any]) -> list[dict[str, Any]]:
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
    return rows


def _total(daily_rows: list[dict[str, Any]]) -> Optional[float]:
    values = [r["precipitation_mm"] for r in daily_rows if r["precipitation_mm"] is not None]
    return round(sum(values), 2) if values else None


def fetch_archive_recent(
    latitude: float,
    longitude: float,
    *,
    past_days: int = 7,
) -> dict[str, Any]:
    """
    Fetch completed past days from Open-Meteo Archive (ERA5-based).
    Ends yesterday in Africa/Windhoek — today is incomplete for archive.
    """
    history = max(1, min(int(past_days), 92))
    today = datetime.now(NAMIBIA_TZ).date()
    end = today - timedelta(days=1)
    start = end - timedelta(days=history - 1)
    payload = _request_json(
        _archive_url(),
        {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min",
            "timezone": "Africa/Windhoek",
        },
    )
    rows = _rows_from_daily(payload.get("daily") or {})
    return {
        "latitude": payload.get("latitude", latitude),
        "longitude": payload.get("longitude", longitude),
        "elevation_m": payload.get("elevation"),
        "timezone": payload.get("timezone", "Africa/Windhoek"),
        "recent_daily": rows,
        "total_recent_precipitation_mm": _total(rows),
        "source": "open-meteo-archive",
        "window": {"start": start.isoformat(), "end": end.isoformat()},
    }


def fetch_forecast(
    latitude: float,
    longitude: float,
    *,
    forecast_days: int = DEFAULT_FORECAST_DAYS,
    past_days: int = 7,
    prefer_archive_for_recent: bool = True,
) -> dict[str, Any]:
    """
    Fetch recent + forecast daily rainfall/temperature for a coordinate.

    Recent rainfall prefers Open-Meteo Archive when available (more faithful history).
    Forecast always comes from the forecast API. Split on Africa/Windhoek "today".
    """
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

    payload = _request_json(_base_url(), params)
    rows = _rows_from_daily(payload.get("daily") or {})

    today = datetime.now(NAMIBIA_TZ).date().isoformat()
    recent_daily = [r for r in rows if r["date"] < today]
    forecast_daily = [r for r in rows if r["date"] >= today]
    recent_source = "open-meteo-forecast-past_days"
    archive_meta: dict[str, Any] = {}

    if prefer_archive_for_recent and history > 0:
        try:
            archive = fetch_archive_recent(latitude, longitude, past_days=history)
            if archive.get("recent_daily"):
                # Keep archive precip; merge temps if forecast past had them
                by_date = {r["date"]: r for r in recent_daily}
                merged = []
                for row in archive["recent_daily"]:
                    fc = by_date.get(row["date"]) or {}
                    merged.append(
                        {
                            "date": row["date"],
                            "precipitation_mm": row.get("precipitation_mm"),
                            "precipitation_probability_max": None,
                            "temperature_max_c": row.get("temperature_max_c")
                            if row.get("temperature_max_c") is not None
                            else fc.get("temperature_max_c"),
                            "temperature_min_c": row.get("temperature_min_c")
                            if row.get("temperature_min_c") is not None
                            else fc.get("temperature_min_c"),
                        }
                    )
                recent_daily = merged
                recent_source = "open-meteo-archive"
                archive_meta = {
                    "archive_window": archive.get("window"),
                    "archive_total_mm": archive.get("total_recent_precipitation_mm"),
                }
        except WeatherServiceError:
            # Fall back silently to forecast past_days
            pass

    return {
        "latitude": payload.get("latitude", latitude),
        "longitude": payload.get("longitude", longitude),
        "elevation_m": payload.get("elevation"),
        "timezone": payload.get("timezone", "Africa/Windhoek"),
        "utc_offset_seconds": payload.get("utc_offset_seconds"),
        "forecast_days": days,
        "past_days": history,
        "recent_daily": recent_daily,
        "forecast_daily": forecast_daily,
        "total_recent_precipitation_mm": _total(recent_daily),
        "total_forecast_precipitation_mm": _total(forecast_daily),
        "source": "open-meteo",
        "recent_source": recent_source,
        "forecast_source": "open-meteo-forecast",
        "namibia_today": today,
        **archive_meta,
    }
