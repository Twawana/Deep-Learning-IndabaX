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
    response_description="Recent rainfall and forecast from Open-Meteo at dataset coordinates.",
)
def weather_by_region(
    region: str = Path(
        ...,
        description="Site, ecoregion, or place alias used to resolve coordinates.",
        examples=["Molly"],
    ),
    forecast_days: int = Query(default=7, ge=1, le=16, description="Forecast horizon in days."),
    past_days: int = Query(default=7, ge=0, le=92, description="Recent history days from Open-Meteo."),
) -> dict:
    """
    Resolve coordinates from the processed dataset, then call Open-Meteo (no API key).

    Rainfall is from model grid points at research-plot mean coordinates — not a farm station.
    """
    return get_weather(region, forecast_days=forecast_days, past_days=past_days)
