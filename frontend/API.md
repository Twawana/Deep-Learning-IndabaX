# Farmar ↔ FastAPI wiring

Base URL: `http://localhost:8000` (set `VITE_API_BASE_URL`)

The React app talks to the IndabaX **FastAPI** backend. It does not call Open-Meteo or CSV files directly.

## Endpoints used by the UI

| UI | Method | Backend route |
|----|--------|----------------|
| Home | `GET` | `/dashboard?location=&herd_size=` |
| Ask | `POST` | `/chat` |
| Pasture | `GET` | `/pasture/{region}` |
| Weather | `GET` | `/weather/{region}` |
| (optional) | `POST` | `/advisor` |
| (optional) | `GET` | `/sites` |

## Chat (`POST /chat`)

Pre-Gemini: backend tools build a plain-language summary with `response`, `reasoning`, `recommendations`, `tools_used`, `sources`, `limitations`.

Later: replace internals with Gemini tool-calling while keeping this response shape.

## Pasture / weather notes

- Location names like **Gobabis** map via backend place aliases to a single research site (**Molly**), not the whole Central Kalahari ecoregion.
- Weather uses **dataset coordinates**, not phone GPS.
- Fields such as `carrying_capacity`, `ndvi`, `soil_quality` are **not** in the processed dataset and stay null / listed in limitations.
