"""Weather API routes."""

from __future__ import annotations

from fastapi import APIRouter, Path, Query

from models.schemas import WeatherResponse
from tools.weather_tool import get_weather

router = APIRouter(tags=["weather"])


@router.get(
    "/weather/{region}",
    response_model=WeatherResponse,
    summary="Get rainfall / weather for a location",
    response_description="Recent rainfall (archive preferred) and forecast from Open-Meteo; lat/lon preferred when provided.",
)
def weather_by_region(
    region: str = Path(
        ...,
        description="Site, ecoregion, or place alias used to resolve coordinates.",
        examples=["Molly"],
    ),
    forecast_days: int = Query(default=7, ge=1, le=16, description="Forecast horizon in days."),
    past_days: int = Query(default=7, ge=0, le=92, description="Recent history days from Open-Meteo."),
    lat: float | None = Query(default=None, description="Optional farmer/town latitude (preferred)."),
    lon: float | None = Query(default=None, description="Optional farmer/town longitude (preferred)."),
) -> dict:
    """
    Resolve a location, then call Open-Meteo (no API key).

    Prefer lat/lon when provided so Gobabis town weather is not pulled from Molly
    research plots ~80 km east. Rainfall is model-grid, not a farm gauge.
    """
    return get_weather(
        region,
        forecast_days=forecast_days,
        past_days=past_days,
        latitude=lat,
        longitude=lon,
    )
