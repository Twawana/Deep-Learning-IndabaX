# Farmar ↔ FastAPI wiring

Base URL: `http://localhost:8000` (set `VITE_API_BASE_URL`)

The React app talks to the IndabaX **FastAPI** backend. It does not call Open-Meteo or CSV files directly.

## Endpoints used by the UI

| UI | Method | Backend route |
|----|--------|----------------|
| Home (decision dashboard) | `GET` | `/dashboard?location=&herd_size=&land_tenure=` |
| Ask | `POST` | `/chat` |
| Pasture | `GET` | `/pasture/{region}` (+ dashboard `decision` for summaries) |
| Rainfall | `GET` | `/weather/{region}` (+ dashboard `decision.rainfall_impact`) |
| Scenario planner | `POST` | `/scenarios` |
| Compare camps | `GET` | `/compare?location_a=&location_b=` |
| Map markers | `GET` | `/sites` |
| (optional) | `POST` | `/advisor` |

## Decision block (`decision`)

Returned by `/dashboard`, `/chat`, `/scenarios`, and compare enrichment.

```text
decision: {
  action_priority: stay | monitor | move_soon | move_now
  headline, recommended_action
  grazing_conditions: { overall_status, pasture_summary, rainfall_summary, combined_assessment }
  rainfall_impact: { outlook, impact_bullets, details }
  pasture_health: { level, label, summary, technical[] }
  timeline: [{ when, status, label, note }]
  explainer: { what, why[], what_if_not, monitor_next[], checks[] }
  confidence: { level, explanation }
  tenure_tone: communal | commercial | conservancy | unknown
}
```

Built by `backend/services/decision_service.py` from existing pasture/weather/grazing tools.
Does **not** invent NDVI, carrying capacity, or rainfall.

## Chat (`POST /chat`)

Pre-Gemini: natural advisor prose + structured `decision` + `reasoning` / `recommendations` / `tools_used` / `sources` / `limitations`.

Free tier still receives a short action + compact why-checks (not a black box).
Premium receives full evidence and timeline-ready decision payload.

## Scenarios (`POST /scenarios`)

What-if planner inputs: `scenario_herd_size`, `assume_rain_mm`, `move_in_days`, `alternate_location`.

Returns `current` vs `scenario` decisions plus `what_changed` notes.
Assumed rain is hypothetical only — vegetation growth is never fabricated.

## Compare (`GET /compare`)

Pasture deltas plus farmer summary and per-side decision snippets.

## Pasture / weather notes

- **Gobabis** maps to research site **Molly** (not the whole Central Kalahari).
- Weather uses **dataset coordinates**, not phone GPS.
- `carrying_capacity` / `ndvi` stay unavailable and are explained under Technical Details.
- Weather tab is labelled **Rainfall** in the UI; route remains `/weather`.
