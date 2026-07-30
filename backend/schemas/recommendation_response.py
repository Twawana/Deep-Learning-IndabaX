"""
Recommendation Response Schema
"""

from pydantic import BaseModel, Field


class RecommendationResponse(BaseModel):
    recommendation: str = Field(
        description="The main recommendation for the farmer."
    )

    reason: str = Field(
        description="The explanation behind the recommendation."
    )

    actions: list[str] = Field(
        description="A list of practical actions the farmer should take."
    )

    risk_level: str = Field(
        description="Overall grazing risk level. Must be Low, Moderate, or High."
    )