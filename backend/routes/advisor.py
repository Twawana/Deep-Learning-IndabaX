"""
Advisor context endpoint — gathers tool outputs for a future Gemini agent.

Does NOT answer the farmer question. Returns structured decision-support context only.
"""

from __future__ import annotations

from fastapi import APIRouter

from models.schemas import AdvisorRequest, AdvisorResponse
from services.transparency import confidence_from_limitations, merge_limitations
from tools.compare_tool import compare_locations
from tools.grazing_tool import calculate_grazing_pressure
from tools.pasture_tool import get_pasture_data
from tools.weather_tool import get_weather

router = APIRouter(tags=["advisor"])


@router.post(
    "/advisor",
    response_model=AdvisorResponse,
    summary="Build AI advisor context package",
    response_description="Structured pasture, weather, herd, and grazing context for Gemini.",
)
def advisor_context(body: AdvisorRequest) -> dict:
    """
    Prepare information needed by an AI advisor.

    This endpoint does **not** interpret or answer the farmer's question.
    It gathers pasture data, weather, herd context, and a grazing assessment
    so a future Gemini agent can reason and respond.
    """
    pasture_data = get_pasture_data(body.region)
    weather_data = get_weather(body.region, forecast_days=body.forecast_days)
    grazing_assessment = calculate_grazing_pressure(
        body.region,
        herd_size=body.herd_size,
        animal_type=body.animal_type,
        pasture_data=pasture_data,
    )

    comparison = None
    if body.compare_region:
        comparison = compare_locations(body.region, body.compare_region)

    herd_context = {
        "herd_size": body.herd_size,
        "animal_type": body.animal_type,
        "provided": body.herd_size is not None or body.animal_type is not None,
    }

    limitations = merge_limitations(
        pasture_data.get("limitations") or [],
        weather_data.get("limitations") or [],
        grazing_assessment.get("limitations") or [],
        (comparison or {}).get("limitations") or [],
    )
    if not pasture_data.get("found"):
        limitations = merge_limitations(limitations, ["Pasture location not found"])
    if not weather_data.get("found"):
        limitations = merge_limitations(limitations, ["Weather location not resolved"])

    confidence = confidence_from_limitations(limitations, high_max=1, medium_max=5)
    # Advisor packages are almost never "high" without carrying capacity + fresh field data
    if confidence == "high":
        confidence = "medium"

    return AdvisorResponse(
        question=body.question,
        location=body.region,
        pasture_data=pasture_data,
        weather_data=weather_data,
        herd_context=herd_context,
        grazing_assessment=grazing_assessment,
        comparison=comparison,
        limitations=limitations,
        confidence=confidence,  # type: ignore[arg-type]
    ).model_dump()
