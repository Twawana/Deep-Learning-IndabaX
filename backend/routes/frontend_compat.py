"""
Frontend-facing chat + dashboard routes.

Reuse existing pasture/weather/grazing tools. Chat is pre-Gemini (deterministic summary).
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from services.frontend_bridge import build_chat_response, build_dashboard
from tools.grazing_tool import calculate_grazing_pressure
from tools.pasture_tool import get_pasture_data
from tools.weather_tool import get_weather

router = APIRouter(tags=["frontend"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    location: Optional[str] = None
    nearest_town: Optional[str] = None
    region: Optional[str] = None
    herd_size: Optional[int] = None
    livestock_type: Optional[str] = None
    animal_type: Optional[str] = None
    farmer_name: Optional[str] = None
    farm_name: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    history: list[dict[str, Any]] = Field(default_factory=list)

    # Extra farm profile fields accepted and ignored for now (forward-compatible)
    phone: Optional[str] = None
    village: Optional[str] = None
    camp_name: Optional[str] = None
    number_of_camps: Optional[int] = None
    farm_size_ha: Optional[float] = None
    land_tenure: Optional[str] = None
    water_source: Optional[str] = None
    farm_notes: Optional[str] = None


def _resolve_location(body: ChatRequest) -> str:
    for candidate in (body.location, body.nearest_town, body.region):
        if candidate and str(candidate).strip():
            return str(candidate).strip()
    return "Gobabis"


@router.post(
    "/chat",
    summary="Farmer chat (tool-backed, pre-Gemini)",
    response_description="Plain-language summary + reasoning from backend tools.",
)
def chat(body: ChatRequest) -> dict[str, Any]:
    """
    Farmar Ask-tab endpoint.

    Uses pasture, weather, and grazing tools to build a response shaped for the frontend.
    Does **not** call Gemini yet — replace internals later with real agent reasoning.
    """
    location = _resolve_location(body)
    animal = body.livestock_type or body.animal_type

    pasture_data = get_pasture_data(location)
    weather_data = get_weather(location)
    grazing = calculate_grazing_pressure(
        location,
        herd_size=body.herd_size,
        animal_type=animal,
    )

    limitations = list(
        dict.fromkeys(
            (pasture_data.get("limitations") or [])
            + (weather_data.get("limitations") or [])
            + (grazing.get("limitations") or [])
        )
    )
    advisor = {
        "pasture_data": pasture_data,
        "weather_data": weather_data,
        "grazing_assessment": grazing,
        "limitations": limitations,
        "confidence": grazing.get("confidence")
        or pasture_data.get("confidence")
        or weather_data.get("confidence")
        or "low",
    }
    return build_chat_response(message=body.message, location=location, advisor=advisor)


@router.get(
    "/dashboard",
    summary="Home dashboard aggregate",
)
def dashboard(
    location: str = Query(default="Gobabis"),
    region: Optional[str] = Query(default=None),
    lat: Optional[float] = Query(default=None),
    lon: Optional[float] = Query(default=None),
    herd_size: Optional[int] = Query(default=None),
) -> dict[str, Any]:
    """Compose weather + pasture cards for the Farmar home screen."""
    query = (location or region or "Gobabis").strip()
    pasture_data = get_pasture_data(query)
    weather_data = get_weather(query)
    grazing = None
    if herd_size is not None:
        grazing = calculate_grazing_pressure(query, herd_size=herd_size, animal_type="cattle")
    return build_dashboard(
        location=query,
        pasture_data=pasture_data,
        weather_data=weather_data,
        grazing=grazing,
    )
