"""
Pasture Data Model

Represents pasture information retrieved from the database.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class PastureData(BaseModel):
    # General Information
    region: str
    season: str

    # Optional Location Information
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    survey_date: Optional[date] = None

    # Optional Vegetation Information
    dominant_plant_species: Optional[str] = None

    # Pasture Health
    vegetation_cover_percent: float
    ndvi: float
    grass_biomass_kg_per_ha: float

    # Bush Condition
    bush_encroachment_level: str

    # Rainfall
    rainfall_last_30_days_mm: float

    # Grazing Information
    livestock_density_lsu_per_ha: float
    estimated_carrying_capacity_ha_per_lsu: float
    grazing_pressure: str