from schemas.pasture_data import PastureData
from schemas.weather_data import WeatherData


def build_prompt(
    farmer_question: str,
    pasture_data: PastureData,
    weather_data: WeatherData,
) -> str:

    return f"""
Farmer Question:
{farmer_question}

Pasture Information
-------------------
Region: {pasture_data.region}
Season: {pasture_data.season}
Dominant Plant Species: {pasture_data.dominant_plant_species}
Vegetation Cover: {pasture_data.vegetation_cover_percent}%
NDVI: {pasture_data.ndvi}
Grass Biomass: {pasture_data.grass_biomass_kg_per_ha} kg/ha
Bush Encroachment: {pasture_data.bush_encroachment_level}
Rainfall (30 days): {pasture_data.rainfall_last_30_days_mm} mm
Livestock Density: {pasture_data.livestock_density_lsu_per_ha}
Carrying Capacity: {pasture_data.estimated_carrying_capacity_ha_per_lsu}
Grazing Pressure: {pasture_data.grazing_pressure}

Weather Information
-------------------
Temperature: {weather_data.temperature_celsius} °C
Rainfall: {weather_data.rainfall_mm} mm
Humidity: {weather_data.humidity_percent}%
Wind Speed: {weather_data.wind_speed_kmh} km/h
"""