# Deep Learning IndabaX Namibia 2026 - AI Rangeland Advisor

Hackathon project: AI tools for Namibian livestock farmers (pasture + weather + chat UI).

## Repo layout

```
backend/     FastAPI API, tools, Supabase (or local CSV) data
frontend/    Farmar React (Vite) mobile + desktop UI
```

## Data source (Supabase)

With `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` in `backend/.env`, the API reads:

| Table | Contents |
|-------|----------|
| `range_sites` | Lacuna field advisory rows |
| `range_landsites` | Synthetic survey (mapped at runtime) |
| `users` | Farmar accounts |

Set `DATA_SOURCE=csv` to force the local `advisory_dataset.csv` fallback.

## Important: raw dataset is NOT in git

The Kaggle Lacuna raw dataset (Excel forms + ~900 field photos) is **large** and is **gitignored**.

| Path | In git? | Notes |
|------|---------|--------|
| `backend/data/raw/` | No | Download locally (see below) |
| `backend/data/processed/advisory_dataset.csv` | Yes | Slim table the API uses at runtime |
| `backend/data/processed/advisory_dataset_summary.json` | Yes | Metadata / null rates |

Do **not** commit `backend/data/raw/` or photos - they will bloat clones and break lightweight deploys.

### Get the raw dataset (local / reprocessing only)

1. Download [farm4tradesrl/lacuna](https://www.kaggle.com/datasets/farm4tradesrl/lacuna) from Kaggle.
2. Unzip into `backend/data/raw/` (so you see folders like `fieldform_cover/`, `pictures/`, etc.).
3. Optional helper:

```bash
cd backend
python scripts/download_dataset.py --source "C:/path/to/unzipped/lacuna"
```

4. Rebuild the processed CSV if needed:

```bash
cd backend
python scripts/process_dataset.py
```

### Deploy / run API without raw files

Runtime only needs:

- `backend/data/processed/advisory_dataset.csv`
- Python deps from `backend/requirements.txt`
- Network access to Open-Meteo

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Frontend

```bash
cd frontend
cp .env.example .env   # VITE_API_BASE_URL=http://localhost:8000
npm.cmd install        # use npm.cmd on Windows if PowerShell blocks npm
npm.cmd run dev
```

See `frontend/README.md` and `frontend/API.md` for UI to API wiring.

## Backend docs

See `BACKEND_STATUS.md` for phases, endpoints, and tool design.
