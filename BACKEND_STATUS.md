# AI Rangeland Advisor - Backend Status

Deep Learning IndabaX Namibia 2026 Hackathon project.

This document records everything built so far for the backend foundation.

---

## Status (what is done now)

| Phase | Status | Description |
|-------|--------|-------------|
| **1 - Dataset discovery** | Done | Local raw data inspected; columns and relationships mapped |
| **2 - Preprocessing** | Done | Clean advisory dataset built from raw Excel forms |
| **3 - Tools** | Done | `get_pasture_data` and `get_weather` tool interfaces |
| **4 - FastAPI** | Done | REST endpoints for health, pasture, weather, sites |
| **Supabase upload** | Not started | Planned next for PostgreSQL persistence |
| **Gemini agent** | Not started | Future tool-calling integration |
| **Frontend** | Wired | Farmar React app uses FastAPI (`/chat`, `/dashboard`, `/pasture`, `/weather`) |

**Important design rule:** the AI / API never reads raw research Excel files directly. Only the processed advisory dataset is queried.

**Dataset in git:** `backend/data/raw/` is **gitignored** (too large for deploy). Runtime uses `backend/data/processed/advisory_dataset.csv` only. See root `README.md` for download instructions.

---

## Goal

Help Namibian livestock farmers make grazing decisions using:

1. Namibia Rangeland and Pasture Dataset (Kaggle: `farm4tradesrl/lacuna`)
2. Rainfall / weather from Open-Meteo
3. (Future) Gemini LLM tool calling
4. (Future) Voice STT/TTS and Vercel AI SDK frontend

---

## Project structure

```
backend/
├── data/
│   ├── raw/                          # LOCAL ONLY (gitignored) — Kaggle Lacuna unzip
│   └── processed/
│       ├── advisory_dataset.csv      # In git — farmer-facing table (tools/API)
│       └── advisory_dataset_summary.json
├── scripts/
│   ├── download_dataset.py           # Optional kagglehub / copy helper
│   ├── inspect_dataset.py            # Phase 1 discovery
│   └── process_dataset.py            # Phase 2 pipeline
├── services/
│   ├── dataset_service.py            # Load/query processed CSV
│   ├── weather_service.py            # Open-Meteo client
│   ├── grazing_service.py
│   ├── transparency.py
│   └── frontend_bridge.py            # Chat/dashboard shaping for Farmar UI
├── tools/
│   ├── pasture_tool.py
│   ├── weather_tool.py
│   ├── grazing_tool.py
│   ├── compare_tool.py
│   └── registry.py
├── models/
│   └── schemas.py
├── routes/
│   ├── pasture.py
│   ├── weather.py
│   ├── advisor.py
│   ├── compare.py
│   └── frontend_compat.py            # POST /chat, GET /dashboard
├── main.py
├── requirements.txt
└── .env.example
```

---

## Phase 1 - Dataset discovery

Source: Kaggle `farm4tradesrl/lacuna`, unzipped into `backend/data/raw/` (Kaggle download skipped because data was already local).

### Raw folders

| Folder | Contents |
|--------|----------|
| `fieldform_cover/` | 80 Excel files - vegetation pin-hit cover by functional group |
| `fieldform_grazing/` | 15 Excel files - livestock, rotational grazing, recorded rainfall |
| `fieldform_quant/` | 20 Excel files - woody plant / bush measurements |
| `fieldform_standing/` | 20 Excel files - standing crop estimates |
| `other_data/` | `Biomass.xlsx`, `dominant_species.xlsx` |
| `supportive_material/` | Coordinates, site/ecoregion names, maps, manual PDF |
| `pictures/` | ~888 field photos (not used in advisory tables) |

### 20 research sites

| Code | Site name | Ecoregion (examples) |
|------|-----------|----------------------|
| agag | Agagia | Thornbush shrubland |
| beul | Beulah | Karstveld |
| busc | Buschpfanne | Dwarf shrub-southern Kalahari |
| cala | Cala | Central Kalahari |
| ghau | Ghaub | Karstveld |
| keet | Keetmanshop | Karas dwarf shrubland |
| kmqs | Katima Mulilo Quarantine Station | NE Kalahari woodland |
| lard | Lardner | Thornbush shrubland |
| moll | Molly | Central Kalahari |
| neud | Neudamm | Highland shrubland |
| ogon | Ogongo | Cuvelai / Western Kalahari |
| ohak | Ohakaua | Thornbush shrubland |
| okah | Okahambo | Northern Kalahari |
| okar | Okarandu | Western highland |
| okon | Okongo | NE Kalahari woodland |
| olif | Olifantswater West | Southern Kalahari |
| onam | Onamundidi | NE Kalahari / Cuvelai |
| sude | Suederecke | Dwarf shrub savannah |
| tira | Tiras | Desert-dwarf shrub transition |
| uuko | Uukolonkadhi | Western highland / Kalahari |

Each site typically has ~3 plots (e.g. `agag_1`, `agag_2`, `agag_3`).

Survey seasons in filenames: `feb_23`, `may_23`, `feb_24`, `april_24`.

### Key raw columns discovered

- **Cover:** `plot_name`, `date`, `lat`, `long`, `functional_group`, `presence`, `G%`, `NG%`
- **Functional groups:** tree, shrub, short_shrub, forb, perennial_grass, annual_grass, litter, bare_ground
- **Grazing:** cattle/sheep/goat presence and counts, `rotational_grazing`, `rainfall`
- **Quant:** woody species, heights, canopy diameters, seedlings
- **Standing:** `standing_crop_estimate`, `max_height`, `old_standing_%`
- **Coords / sites:** `Ecoregion`, `Site Name`, `Plot Name`, `Latitude`, `Longitude`

**Note:** Town names like "Gobabis" are not site names. Closest dataset match is **Central Kalahari** (sites **Cala** and **Molly**), exposed via a place alias in the backend.

Inspection script: `python scripts/inspect_dataset.py`

---

## Phase 2 - Preprocessing

Built by:

```bash
cd backend
python scripts/process_dataset.py
```

### Output grain

One row per **plot x observation_date** (230 rows from cover surveys), joined with standing, biomass, grazing, quant, and dominant species where available.

Outputs:

- `data/processed/advisory_dataset.csv`
- `data/processed/advisory_dataset.json`
- `data/processed/advisory_dataset_summary.json`

### Farmer-facing fields

| Field | How it is derived |
|-------|-------------------|
| `region` | Ecoregion from `coordinates_and_species` |
| `site` / `site_code` / `plot_name` | Site registry |
| `latitude` / `longitude` | Site coordinates |
| `observation_date` | Survey date (day-first parsing) |
| `vegetation_cover` | Mean presence % of perennial grass + annual grass + forb |
| `bush_encroachment` | Mean presence % of shrub + short_shrub + tree |
| `biomass` | Prefer `Biomass.xlsx` after-mean; else standing crop mean |
| `grazing_pressure` | Sum of cattle + sheep + goat head counts when recorded |
| `pasture_condition` | Always null - no qualitative label exists in source data |

No fabricated scores. Missing source values stay null.

### Coverage notes

- Grazing forms exist for only some sites/dates (~94% of rows have null `grazing_pressure`)
- Biomass missing on ~27% of rows
- One Neudamm row has date `2024-11-02` as stored in the raw Excel (source quirk)

---

## Phase 3 - Tools

Gemini-ready Python functions (return clean JSON dicts).

### `get_pasture_data(region: str)`

File: `tools/pasture_tool.py`

- Searches processed dataset by site, site code, ecoregion, plot, or place alias
- Returns latest observation per plot by default
- If not found:

```json
{
  "found": false,
  "message": "Region not found"
}
```

### `get_weather(region: str)`

File: `tools/weather_tool.py`

1. Resolve region to coordinates from processed data
2. Call Open-Meteo (`https://api.open-meteo.com/v1/forecast`) - no API key
3. Return daily rainfall / temperature forecast
4. Readable errors on timeout or HTTP failure

### Place aliases (examples)

| Farmer query | Maps to |
|--------------|---------|
| Gobabis | Central Kalahari (Cala, Molly) |
| Windhoek | Neudamm |
| Keetmanshoop | Keetmanshop |

---

## Phase 4 - FastAPI

### Run

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

- App: http://127.0.0.1:8000/
- Interactive docs: http://127.0.0.1:8000/docs

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health: `{"status":"Rangeland Advisor API running"}` |
| `GET` | `/pasture/{region}` | Pasture info (`?include_history=true` optional) |
| `GET` | `/weather/{region}` | Rainfall forecast (`?forecast_days=7`) |
| `GET` | `/sites` | List of 20 research sites |

### Example

```text
GET /pasture/Gobabis
-> found=true, sites=[Cala, Molly], latest_by_plot=[...]

GET /weather/Molly
-> Open-Meteo 7-day precip/temp for Molly coordinates

GET /pasture/Nowhere
-> {"found": false, "message": "Region not found"}
```

### Environment

Copy `.env.example` to `.env` if needed:

- `ADVISORY_DATASET_PATH` - optional override for processed CSV
- `OPEN_METEO_BASE_URL` - default Open-Meteo forecast URL
- `OPEN_METEO_TIMEOUT_SECONDS` - request timeout
- Future: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_TABLE`

---

## Data pipeline architecture

```
Raw Kaggle / local Excel forms
        |
scripts/inspect_dataset.py   (discover structure)
        |
scripts/process_dataset.py   (clean + aggregate)
        |
data/processed/advisory_dataset.csv
        |
services/dataset_service.py
        |
tools/pasture_tool.py  +  tools/weather_tool.py (+ Open-Meteo)
        |
FastAPI routes
        |
(Future) Gemini agent tool calling
(Future) Supabase / PostgreSQL
(Future) Frontend (Vercel AI SDK)
```

---

## Tech stack

**Now**

- Python, FastAPI, Pydantic
- Pandas, openpyxl
- Requests (Open-Meteo)
- python-dotenv

**Planned**

- Supabase / PostgreSQL upload of advisory rows
- Gemini LLM with tool calling
- Vercel AI SDK frontend
- Speech-to-text / text-to-speech

---

## Next steps

1. **Supabase upload** - table schema + script to push `advisory_dataset.csv`
2. Optionally point `dataset_service` at Supabase instead of local CSV
3. Gemini tool-calling agent using `get_pasture_data` / `get_weather`
4. Frontend chat UI
5. Voice interaction

---

## Quick commands cheat sheet

```bash
# Re-inspect raw data
python scripts/inspect_dataset.py

# Rebuild processed advisory dataset
python scripts/process_dataset.py

# Run API
uvicorn main:app --reload --port 8000
```

If port 8000 is busy on Windows (`WinError 10013`):

```powershell
netstat -ano | findstr :8000
taskkill /PID <pid> /F
# or use another port
uvicorn main:app --reload --port 8001
```
