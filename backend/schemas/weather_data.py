"""
 weather data model
represents weather information used by the AI assistant.
"""

from pydantic import BaseModel

class WeatherData(BaseModel):
    temperature_celsius: float
    rainfall_mm: float
    wind_speed_kmh: float
    humidity_percent: float