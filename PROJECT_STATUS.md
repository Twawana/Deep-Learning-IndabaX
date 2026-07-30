# AI Rangeland Advisor - Overall Project Status

Deep Learning IndabaX Namibia 2026 hackathon project.

This document captures the current state of the full project: data pipeline, backend functions/routes, frontend features, speech features, known constraints, and next steps.

---

## 1) Project Objective

Build an AI-powered **decision support system** for Namibian communal and commercial livestock farmers — not a chatbot that only displays environmental statistics.

It combines:

- Historical pasture/rangeland observations (Lacuna field + synthetic_v2 merged)
- Near-term weather/rainfall context (Open-Meteo)
- Farmer profile context (location, herd, land tenure, farm size, farm notes)
- Intent-routed tools (stocking, year-over-year, tenure peers) + decision layer
- Natural-language chat guidance (tool-backed now, Gemini planned next)

Primary farmer questions: Can my herd stay? Should I move? Is grass recovering? Is rainfall enough?

---

## 1b) Decision-support UX (current)

Homepage is a grazing management dashboard:

1. Action priority (Stay / Monitor / Prepare to Move / Move Herd)
2. Grazing Conditions summary (pasture + rainfall + combined assessment)
3. Decision timeline (today → 14 days planning aid)
4. Pasture Health (farmer summary + expandable technical details)
5. Rainfall & Grass Recovery (impact first; raw mm under details)
6. Why this recommendation? (checks + expandable evidence)
7. Ask advisor / Scenario planner / Compare camps

Pasture page includes a **satellite site map** (Leaflet + Esri World Imagery).
Chat uses extension-officer prose and attaches the same `decision` transparency block.

Backend decision layer: `backend/services/decision_service.py`
New routes: `POST /scenarios`, enriched `GET /compare`

---

## 2) High-Level Architecture

```text
Farmer (mobile/web UI)
  -> Farmar Frontend (React + Vite)
      -> FastAPI Backend
          -> Processed advisory dataset (CSV)
          -> Open-Meteo API
```

Core design rule:

- Runtime logic never reads raw research Excel/Numbers files directly.
- Runtime reads only `backend/data/processed/advisory_dataset.csv`.
- That CSV combines Lacuna field plots (`lacuna_field`) and the synthetic
  Namibia rangeland dataset (`synthetic_v2`, converted from `.numbers`).

---

## 3) Detailed Project Structure

```text
Deep-Learning-IndabaX/
├── backend/
│   ├── data/
│   │   ├── raw/                          # Local only, gitignored (.numbers / Lacuna unzip)
│   │   └── processed/
│   │       ├── advisory_dataset.csv      # Runtime dataset (Lacuna + synthetic)
│   │       ├── synthetic_dataset.csv     # Mapped synthetic archive
│   │       ├── advisory_dataset.json
│   │       └── advisory_dataset_summary.json
│   ├── scripts/
│   │   ├── download_dataset.py           # Optional helper to copy/download raw dataset
│   │   ├── inspect_dataset.py            # Dataset schema/column inspection
│   │   ├── process_dataset.py            # Lacuna raw -> processed advisory table
│   │   └── convert_and_merge_synthetic.py # Numbers/CSV synthetic -> merge into advisory
│   ├── models/
│   │   └── schemas.py                    # Pydantic request/response models
│   ├── services/
│   │   ├── dataset_service.py            # CSV loading, query resolution, alias mapping
│   │   ├── weather_service.py            # Open-Meteo client + timezone split
│   │   ├── grazing_service.py            # Grazing heuristics
│   │   ├── decision_service.py           # Action priority, timeline, rainfall impact, explainer
│   │   ├── transparency.py               # Confidence/limitations helpers
│   │   └── frontend_bridge.py            # Shape backend outputs for Farmar UI
│   ├── tools/
│   │   ├── pasture_tool.py               # get_pasture_data()
│   │   ├── weather_tool.py               # get_weather()
│   │   ├── grazing_tool.py               # calculate_grazing_pressure()
│   │   ├── compare_tool.py               # compare_locations() + farmer summary
│   │   └── registry.py                   # Gemini-ready tool manifest registry
│   ├── routes/
│   │   ├── pasture.py                    # GET /pasture/{region}
│   │   ├── weather.py                    # GET /weather/{region}
│   │   ├── advisor.py                    # POST /advisor
│   │   ├── compare.py                    # GET /compare
│   │   ├── scenarios.py                  # POST /scenarios
│   │   └── frontend_compat.py            # POST /chat, GET /dashboard
│   ├── main.py                           # FastAPI app, CORS, route wiring
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/                   # UI cards, chat, decision/* advisor cards + SiteMap
│   │   ├── context/FarmContext.jsx       # Profile/location state
│   │   ├── hooks/                        # useChat/useDashboard/usePasture/useWeather/useSpeech
│   │   ├── pages/                        # Dashboard/Chat/Pasture/Weather/Scenarios/Compare/Profile
│   │   ├── services/api.js               # HTTP client + response normalization
│   │   └── utils/                        # constants/labels/formatting helpers
│   ├── API.md                            # Frontend-backend contract notes
│   └── README.md
├── README.md
├── BACKEND_STATUS.md
└── PROJECT_STATUS.md
```

---

## 4) Backend Functions and Features (Detailed)

### 4.1 Data Pipeline Features

- `inspect_dataset.py`
  - inventories raw folders/files
  - inspects columns and value patterns
  - helps avoid guessing field names
- `process_dataset.py`
  - merges field forms and supportive material
  - outputs farmer-facing metrics by plot/date
  - preserves nulls when source data is missing
  - does not invent carrying capacity or qualitative condition labels

### 4.2 Core Query and Matching Functions

- `dataset_service.resolve_query(query)`
  - resolves aliases, site names, site codes, plot names, exact regions
  - tightened partial matching to reduce false positives
  - keeps Gobabis mapping explicit (`Gobabis -> Molly`)
- `dataset_service.filter_by_query(query)`
  - returns matching dataframe slice + match metadata
- `dataset_service.nearest_site_by_coordinates(lat, lon)`
  - GPS fallback to nearest known research site
- `dataset_service.list_supported_place_aliases()`
  - exposes aliases to `/sites`

### 4.3 Tool Functions (Gemini-ready interfaces)

- `get_pasture_data(location, include_history=False)`
  - returns pasture metrics + metadata + limitations
  - includes confidence and staleness context
- `get_weather(location, forecast_days=..., past_days=...)`
  - resolves coordinates from dataset
  - calls Open-Meteo
  - splits recent vs forecast windows using Africa/Windhoek date
  - returns `found=false` on weather provider failure
- `calculate_grazing_pressure(location, herd_size=None, animal_type=None, pasture_data=None)`
  - computes grazing risk from available indicators
  - can reuse `pasture_data` to avoid duplicate lookups
  - flags limitation when species-specific calibration is unavailable
- `compare_locations(location_a, location_b)`
  - compares two locations using pasture/weather context

### 4.4 API Route Features

- `GET /`
  - health endpoint
- `GET /pasture/{region}`
  - pasture lookup by site/alias/region/plot/site code
- `GET /weather/{region}`
  - weather lookup for dataset-resolved coordinates
- `POST /advisor`
  - structured context package for future Gemini reasoning
- `GET /compare`
  - side-by-side comparison outputs
- `GET /sites`
  - site list + supported aliases
- `POST /chat` (frontend compatibility)
  - deterministic pre-Gemini answer composition from tool outputs
  - includes `response`, `reasoning`, `recommendations`, `tools_used`, `sources`, `limitations`
- `GET /dashboard` (frontend compatibility)
  - home aggregate payload: weather + pasture + alerts + recommendations

---

## 5) Frontend Features (Detailed)

### 5.1 Functional Pages

- Dashboard (`/`)
  - location picker (supported entries)
  - weather + pasture summary cards
  - alerts/recommendations overview
- Ask (`/chat`)
  - farmer chat flow to `POST /chat`
  - displays reasoning, recommendations, tool names, limitations
  - clear chat action
- Pasture (`/pasture`)
  - detailed pasture metrics card
- Weather (`/weather`)
  - temperature/rain summaries and forecast context
- Profile (`/profile`)
  - farmer identity/farm context/location/herd metadata
  - persisted locally in browser storage

### 5.2 API Hook Features

- `useChat`
  - sends chat payload with profile context + history
  - maps backend payload to UI message model
- `useDashboard`
  - query-keyed by location/herd to refetch correctly
- `usePasture`, `useWeather`
  - fetch location-bound data
  - clear stale data when location changes
- `services/api.js`
  - response normalization for UI-friendly fields
  - explicit location requirement (no silent fallback town)

### 5.3 Speech Features

- Speech-to-text (`useSpeechToText`)
  - mic toggle
  - browser capability detection
  - clearer permission/network/no-speech errors
  - transcript append into chat input
- Text-to-speech (`useTextToSpeech`)
  - per-message Listen/Stop
  - optional auto-read of assistant replies
  - voice fallback selection (`en-ZA`, then `en-GB`/`en-US`)
  - long-response chunking to avoid truncation issues

---

## 6) Recent Stability and Quality Fixes

- removed risky silent defaults for unresolved locations
- tightened query matching to avoid accidental partial-region matches
- made weather date logic Windhoek-time aware
- improved weather error path (`found=false` instead of false success)
- corrected rainfall wording to reflect actual recent window
- reduced duplicate pasture lookups in grazing flow
- constrained CORS for local app origins
- improved chat transparency and UX labels for limitations/tool usage

---

## 7) Data and Git Status Notes

- raw dataset is local only: `backend/data/raw/` (gitignored)
- runtime dataset: `backend/data/processed/advisory_dataset.csv`
- integrated working branch used for app/backend flow: `frontend-dev`
- notable integration commit:
  - `c3dcb10 feijoshow <cristianofeijon@gmail.com>`

---

## 8) Local Run Instructions

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend (Windows/PowerShell)

Use `npm.cmd` if PowerShell execution policy blocks `npm.ps1`.

```bash
cd frontend
npm.cmd install
npm.cmd run dev
```

Environment:

```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## 9) Current Limitations

- Gemini reasoning is not integrated yet (`/chat` is pre-Gemini deterministic composition)
- carrying capacity / LSU-calibrated grazing models are not available in source data
- some metrics are sparse by season/site (nulls are expected and preserved)
- speech support depends on browser Web Speech API quality (best in Chrome/Edge)

---

## 10) Next Planned Work

- integrate Gemini tool-calling in `/chat` while preserving response contract
- add Supabase/PostgreSQL persistence for farmer sessions/history/context
- add automated tests for:
  - dataset query matching
  - tool output contracts
  - route-level integration
  - frontend hook/API behavior
- finalize deployment docs and environment hardening

---

## 11) Key Reference Docs

- `README.md` - repository overview and run instructions
- `BACKEND_STATUS.md` - backend build phases and dataset details
- `frontend/README.md` - frontend app usage and stack
- `frontend/API.md` - frontend-to-backend route contract

