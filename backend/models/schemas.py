"""
Pydantic schemas for the Rangeland Advisor API and Gemini-ready tool I/O.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


Confidence = Literal["high", "medium", "low"]
GrazingRisk = Literal["high", "medium", "low", "unknown"]


class HealthResponse(BaseModel):
    status: str = Field(examples=["Rangeland Advisor API running"])


class PastureMetrics(BaseModel):
    biomass: Optional[float] = None
    vegetation_cover: Optional[float] = None
    bush_encroachment: Optional[float] = None
    cover_perennial_grass_pct: Optional[float] = None
    cover_annual_grass_pct: Optional[float] = None
    cover_bare_ground_pct: Optional[float] = None
    grazing_pressure_recorded: Optional[float] = Field(
        default=None,
        description="Sum of recorded livestock counts from survey forms when available.",
    )


class PastureResponse(BaseModel):
    found: bool
    location: str = Field(description="Original location query from the caller.")
    matched_on: Optional[str] = None
    match_value: Optional[str] = None
    sites: list[str] = Field(default_factory=list)
    pasture: PastureMetrics = Field(default_factory=PastureMetrics)
    observation_date: Optional[str] = Field(
        default=None,
        description="Most recent observation date among matched plots.",
    )
    plot_count: int = 0
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    dominant_herbaceous: Optional[str] = None
    dominant_woody: Optional[str] = None
    details_by_plot: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Latest row per plot for transparency / deeper agent use.",
    )
    limitations: list[str] = Field(default_factory=list)
    confidence: Confidence = "low"
    message: Optional[str] = None


class DailyWeather(BaseModel):
    date: str
    precipitation_mm: Optional[float] = None
    precipitation_probability_max: Optional[float] = None
    temperature_max_c: Optional[float] = None
    temperature_min_c: Optional[float] = None


class RainfallSummary(BaseModel):
    days: int = 0
    total_precipitation_mm: Optional[float] = None
    daily: list[DailyWeather] = Field(default_factory=list)


class WeatherResponse(BaseModel):
    found: bool
    location: str
    matched_on: Optional[str] = None
    match_value: Optional[str] = None
    site: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    recent_rainfall: RainfallSummary = Field(default_factory=RainfallSummary)
    forecast: RainfallSummary = Field(default_factory=RainfallSummary)
    source: Optional[str] = "open-meteo"
    limitations: list[str] = Field(default_factory=list)
    confidence: Confidence = "low"
    message: Optional[str] = None


class GrazingAssessment(BaseModel):
    grazing_risk: GrazingRisk = "unknown"
    reason: str
    confidence: Confidence = "low"
    limitations: list[str] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)
    inputs: dict[str, Any] = Field(default_factory=dict)


class AdvisorRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        description="Farmer natural-language question (not answered by this endpoint).",
        examples=["Can my cattle stay in Gobabis another week?"],
    )
    region: str = Field(
        ...,
        min_length=1,
        description="Location, site, ecoregion, or place alias.",
        examples=["Gobabis"],
    )
    herd_size: Optional[int] = Field(
        default=None,
        ge=0,
        description="Optional herd size supplied by the farmer.",
        examples=[70],
    )
    animal_type: Optional[str] = Field(
        default=None,
        description="Optional animal type, e.g. cattle, goats, sheep.",
        examples=["cattle"],
    )
    compare_region: Optional[str] = Field(
        default=None,
        description="Optional second location for comparison context.",
    )
    forecast_days: int = Field(default=7, ge=1, le=16)


class AdvisorResponse(BaseModel):
    question: str
    location: str
    pasture_data: dict[str, Any] = Field(default_factory=dict)
    weather_data: dict[str, Any] = Field(default_factory=dict)
    herd_context: dict[str, Any] = Field(default_factory=dict)
    grazing_assessment: dict[str, Any] = Field(default_factory=dict)
    comparison: Optional[dict[str, Any]] = None
    limitations: list[str] = Field(default_factory=list)
    confidence: Confidence = "low"
    note: str = Field(
        default=(
            "Context package for an AI advisor. This endpoint does not answer the farmer question."
        )
    )


class CompareRequest(BaseModel):
    location_a: str = Field(..., min_length=1, examples=["Gobabis"])
    location_b: str = Field(..., min_length=1, examples=["Neudamm"])


class CompareResponse(BaseModel):
    found: bool
    location_a: dict[str, Any] = Field(default_factory=dict)
    location_b: dict[str, Any] = Field(default_factory=dict)
    comparison: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    confidence: Confidence = "low"
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    detail: str
    extras: Optional[dict[str, Any]] = None
