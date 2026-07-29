"""
Weather tool — resolve location coordinates from processed data, then call Open-Meteo.

Retrieves rainfall and weather information for a Namibian location.
"""

from __future__ import annotations

from typing import Any

from models.schemas import DailyWeather, RainfallSummary, WeatherResponse
from services import dataset_service
from services.transparency import confidence_from_limitations, merge_limitations
from services.weather_service import WeatherServiceError, fetch_forecast

TOOL_DESCRIPTION = (
    "Retrieves rainfall and weather information for a Namibian location "
    "using coordinates from the processed rangeland dataset and the Open-Meteo API."
)


def get_weather(
    location: str,
    *,
    forecast_days: int = 7,
    past_days: int = 7,
) -> dict[str, Any]:
    """
    Retrieve recent rainfall and forecast for a location/site/region.

    Args:
        location: Namibian place, research site, site code, or ecoregion.
        forecast_days: Forward-looking days (1-16).
        past_days: Recent days from Open-Meteo (0-92).

    Returns:
        Clean JSON with recent_rainfall, forecast, limitations, and confidence.
    """
    query = (location or "").strip()
    if not query:
        return WeatherResponse(
            found=False,
            location=query,
            message="Region not found",
            confidence="low",
            limitations=["No location provided"],
        ).model_dump()

    try:
        matched, matched_on, match_value = dataset_service.filter_by_query(query)
    except FileNotFoundError as exc:
        return WeatherResponse(
            found=False,
            location=query,
            message=str(exc),
            confidence="low",
            limitations=["Processed advisory dataset unavailable"],
        ).model_dump()

    if matched.empty:
        return WeatherResponse(
            found=False,
            location=query,
            message="Region not found",
            confidence="low",
            limitations=["No matching site or region in processed dataset"],
        ).model_dump()

    coords = dataset_service.representative_coordinates(matched)
    if coords is None:
        return WeatherResponse(
            found=False,
            location=query,
            matched_on=matched_on,
            match_value=match_value,
            message="Coordinates unavailable for this region",
            confidence="low",
            limitations=["Coordinates unavailable for this region"],
        ).model_dump()

    latitude, longitude, meta = coords
    limitations = [
        "Rainfall data is from Open-Meteo at the nearest dataset coordinates "
        "(research plot mean), not a farm weather station"
    ]
    if matched_on and "alias" in matched_on:
        limitations.append(
            f"Location '{query}' mapped via place alias to dataset match '{match_value}'"
        )

    try:
        payload = fetch_forecast(
            latitude,
            longitude,
            forecast_days=forecast_days,
            past_days=past_days,
        )
    except WeatherServiceError as exc:
        limitations.append(str(exc))
        return WeatherResponse(
            found=True,
            location=query,
            matched_on=matched_on,
            match_value=match_value,
            site=meta.get("site"),
            region=meta.get("region"),
            latitude=latitude,
            longitude=longitude,
            message=str(exc),
            limitations=merge_limitations(limitations),
            confidence="low",
            source="open-meteo",
        ).model_dump()

    recent_rows = [DailyWeather(**row) for row in payload.get("recent_daily") or []]
    forecast_rows = [DailyWeather(**row) for row in payload.get("forecast_daily") or []]

    if not recent_rows:
        limitations.append("Recent rainfall history unavailable from weather provider")
    if not forecast_rows:
        limitations.append("Forecast rainfall unavailable from weather provider")

    limitations = merge_limitations(limitations)
    confidence = confidence_from_limitations(limitations, high_max=1, medium_max=3)

    return WeatherResponse(
        found=True,
        location=query,
        matched_on=matched_on,
        match_value=match_value,
        site=meta.get("site"),
        region=meta.get("region"),
        latitude=float(payload.get("latitude", latitude)),
        longitude=float(payload.get("longitude", longitude)),
        recent_rainfall=RainfallSummary(
            days=len(recent_rows),
            total_precipitation_mm=payload.get("total_recent_precipitation_mm"),
            daily=recent_rows,
        ),
        forecast=RainfallSummary(
            days=len(forecast_rows),
            total_precipitation_mm=payload.get("total_forecast_precipitation_mm"),
            daily=forecast_rows,
        ),
        source=payload.get("source", "open-meteo"),
        limitations=limitations,
        confidence=confidence,  # type: ignore[arg-type]
    ).model_dump()
