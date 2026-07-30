from fastapi import APIRouter

from schemas.recommendation_request import RecommendationRequest
from schemas.recommendation_response import RecommendationResponse
from services.llm_service import GeminiService

router = APIRouter(
    prefix="/recommendations",
    tags=["Recommendations"],
)

gemini_service = GeminiService()


@router.post("/", response_model=RecommendationResponse)
def generate_recommendation(request: RecommendationRequest):
    """
    Generate a livestock grazing recommendation.
    """

    return gemini_service.generate_recommendation(
        farmer_question=request.farmer_question,
        pasture_data=request.pasture_data,
        weather_data=request.weather_data,
    )