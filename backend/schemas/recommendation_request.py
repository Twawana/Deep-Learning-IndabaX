from pydantic import BaseModel

from schemas.pasture_data import PastureData
from schemas.weather_data import WeatherData


class RecommendationRequest(BaseModel):
    farmer_question: str
    pasture_data: PastureData
    weather_data: WeatherData