"""
Weather tool — resolve location coordinates from processed data, then call Open-Meteo.

Retrieves rainfall and weather information for a Namibian location.
"""

from __future__ import annotations

from typing import Any

from models.schemas import DailyWeather, RainfallSummary, WeatherResponse
from services import dataset_service
from services.connectivity import is_online
from services.transparency import confidence_from_limitations, merge_limitations
from services.weather_service import WeatherServiceError, fetch_forecast

TOOL_DESCRIPTION = (
    "Retrieves rainfall and weather information for a Namibian location "
    "using coordinates from the processed rangeland dataset and the Open-Meteo API. "
    "When offline, skips remote weather and returns a local-only stub."
)


def get_weather(
    location: str,
    *,
    forecast_days: int = 7,
    past_days: int = 7,
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict[str, Any]:
    """
    Retrieve recent rainfall and forecast for a location/site/region.

    If latitude/longitude are provided (farmer GPS / town pin), those are preferred
    for Open-Meteo. Otherwise coordinates come from the matched dataset plots.

    When the device/network looks offline, Open-Meteo is skipped so chat can
    answer from the local advisory dataset only.
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
    if coords is None and (latitude is None or longitude is None):
        return WeatherResponse(
            found=False,
            location=query,
            matched_on=matched_on,
            match_value=match_value,
            message="Coordinates unavailable for this region",
            confidence="low",
            limitations=["Coordinates unavailable for this region"],
        ).model_dump()

    dataset_lat = coords[0] if coords else None
    dataset_lon = coords[1] if coords else None
    meta = coords[2] if coords else {}

    coordinate_source = "dataset_plot_mean"
    use_lat = dataset_lat
    use_lon = dataset_lon
    if _valid_namibia_coords(latitude, longitude):
        use_lat = float(latitude)
        use_lon = float(longitude)
        coordinate_source = "farmer_gps_or_town_pin"

    if not is_online():
        offline = WeatherResponse(
            found=False,
            location=query,
            matched_on=matched_on,
            match_value=match_value,
            site=meta.get("site"),
            region=meta.get("region"),
            latitude=use_lat,
            longitude=use_lon,
            message="Offline — live weather unavailable; using local pasture data only",
            confidence="low",
            limitations=[
                "Device appears offline — Open-Meteo weather skipped",
                "Advice is based on the local advisory dataset only",
            ],
            source="offline-local",
        ).model_dump()
        offline["coordinate_source"] = coordinate_source
        offline["mode"] = "offline"
        return offline

    limitations = [
        "Rainfall is from Open-Meteo model grids — not a farm rain gauge.",
        "Recent totals prefer Open-Meteo Archive; forecast is the forecast model.",
    ]
    if coordinate_source == "farmer_gps_or_town_pin":
        limitations.append(
            f"Weather queried at farmer/town coordinates ({use_lat:.4f}, {use_lon:.4f}), "
            "not the research-plot mean."
        )
        if dataset_lat is not None and dataset_lon is not None:
            limitations.append(
                f"Nearest dataset plot mean is ({dataset_lat:.4f}, {dataset_lon:.4f}) "
                "for pasture metrics."
            )
    else:
        limitations.append(
            "Weather queried at nearest dataset plot-mean coordinates "
            "(research site), not necessarily the town centre."
        )
    if matched_on and "alias" in matched_on:
        limitations.append(
            f"Location '{query}' mapped via place alias to dataset match '{match_value}'"
        )

    try:
        payload = fetch_forecast(
            float(use_lat),
            float(use_lon),
            forecast_days=forecast_days,
            past_days=past_days,
        )
    except WeatherServiceError as exc:
        limitations.append(str(exc))
        return WeatherResponse(
            found=False,
            location=query,
            matched_on=matched_on,
            match_value=match_value,
            site=meta.get("site"),
            region=meta.get("region"),
            latitude=use_lat,
            longitude=use_lon,
            message=str(exc),
            limitations=merge_limitations(limitations),
            confidence="low",
            source="open-meteo",
        ).model_dump()

    recent_rows = [DailyWeather(**row) for row in payload.get("recent_daily") or []]
    forecast_rows = [DailyWeather(**row) for row in payload.get("forecast_daily") or []]

    gap_notes: list[str] = []
    if not recent_rows:
        gap_notes.append("Recent rainfall history unavailable from weather provider")
    if not forecast_rows:
        gap_notes.append("Forecast rainfall unavailable from weather provider")
    limitations.extend(gap_notes)

    limitations = merge_limitations(limitations)
    # Transparency boilerplate (model-grid, coord source) should not force "low".
    # Always at most medium when data exists — this is not a farm rain gauge.
    confidence = confidence_from_limitations(gap_notes, high_max=0, medium_max=1)
    if confidence == "high" and (recent_rows or forecast_rows):
        confidence = "medium"

    result = WeatherResponse(
        found=True,
        location=query,
        matched_on=matched_on,
        match_value=match_value,
        site=meta.get("site"),
        region=meta.get("region"),
        latitude=float(payload.get("latitude", use_lat)),
        longitude=float(payload.get("longitude", use_lon)),
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
    result["coordinate_source"] = coordinate_source
    result["requested_latitude"] = use_lat
    result["requested_longitude"] = use_lon
    result["open_meteo_grid_latitude"] = payload.get("latitude")
    result["open_meteo_grid_longitude"] = payload.get("longitude")
    result["elevation_m"] = payload.get("elevation_m")
    result["timezone"] = payload.get("timezone")
    result["namibia_today"] = payload.get("namibia_today")
    result["recent_source"] = payload.get("recent_source")
    result["forecast_source"] = payload.get("forecast_source")
    return result


def _valid_namibia_coords(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None:
        return False
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return False
    # Rough Namibia bounding box
    return -29.5 <= lat_f <= -16.5 and 11.5 <= lon_f <= 25.5
