"""
Rangeland Advisor API — Namibia livestock grazing decision support.

Run from the backend/ directory:
  uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models.schemas import HealthResponse
from routes import admin, advisor, compare, frontend_compat, pasture, scenarios, sync, weather
from services import dataset_service
from tools.registry import list_tool_manifests

load_dotenv(Path(__file__).resolve().parent / ".env")

app = FastAPI(
    title="Rangeland Advisor API",
    description=(
        "Decision-support backend for the Namibia AI Rangeland Advisor "
        "(Deep Learning IndabaX Namibia 2026).\n\n"
        "This API provides **tools and context** for a future Gemini agent. "
        "It does **not** invent dataset values and does **not** read raw Excel files.\n\n"
        "### Core tool endpoints\n"
        "- `GET /pasture/{region}` — processed rangeland metrics\n"
        "- `GET /weather/{region}` — Open-Meteo rainfall at dataset coordinates\n"
        "- `POST /advisor` — gather pasture + weather + grazing context\n"
        "- `GET /compare` — compare two locations\n"
        "- `GET /tools` — Gemini-ready tool manifests\n\n"
        "### Farmar frontend adapters\n"
        "- `POST /chat` — Oryx agent (Gemini tool-calling) + Farmar response\n"
        "- `GET /dashboard` — Home screen aggregate\n"
        "- `POST /sync/push` — device offline queue → Supabase PostgreSQL\n"
    ),
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pasture.router)
app.include_router(weather.router)
app.include_router(advisor.router)
app.include_router(compare.router)
app.include_router(scenarios.router)
app.include_router(frontend_compat.router)
app.include_router(admin.router)
app.include_router(sync.router)


@app.get(
    "/",
    response_model=HealthResponse,
    summary="Health check",
    tags=["health"],
)
def root() -> dict[str, str]:
    """Confirm the Rangeland Advisor API is running."""
    return {"status": "Rangeland Advisor API running"}


@app.get("/sites", tags=["meta"], summary="List research sites")
def sites() -> dict:
    """List available research sites from the processed advisory dataset."""
    return {
        "sites": dataset_service.list_sites(),
        "aliases": dataset_service.list_supported_place_aliases(),
    }


@app.get("/tools", tags=["meta"], summary="List Gemini-ready tool manifests")
def tools_manifest() -> dict:
    """
    Tool interface descriptions for future Gemini function calling.

    Callables are not exposed over HTTP — only names, descriptions, and parameter schemas.
    """
    return {"tools": list_tool_manifests()}
