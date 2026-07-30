# Deep Learning IndabaX Namibia 2026 - AI Rangeland Advisor

Hackathon project: AI tools for Namibian livestock farmers (pasture + weather + chat UI).

## Repo layout

```
backend/     FastAPI API, tools, Supabase (or local CSV) data
frontend/    Farmar React (Vite) mobile + desktop UI
supabase/    SQL schema for cloud tables
```

## Deployment (Vercel + Supabase + Railway)

```
Browser → Vercel (frontend)
              ↓  VITE_API_BASE_URL
         Railway (FastAPI)
              ↓  service role
         Supabase (Postgres)
```

### 1. Supabase (database)

1. Create a project at [supabase.com](https://supabase.com).
2. In the SQL Editor, run [`supabase/schema.sql`](supabase/schema.sql) if tables are not set up yet.
3. Copy **Project URL** and **service role** key (Settings → API).
4. Backend only uses the **service role** key. Never put it in Vercel or the browser.
5. Optional browser auth: use the **anon** key in frontend env only.

### 2. Railway (Python backend)

1. New project → Deploy from this GitHub repo.
2. Set **Root Directory** to `backend/` (uses [`backend/railway.toml`](backend/railway.toml)).
3. Add variables (see [`backend/.env.example`](backend/.env.example)):

| Variable | Notes |
|----------|--------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend only |
| `GEMINI_API_KEY` | In Vision / Gemini |
| `GEMINI_MODEL` | e.g. `gemini-2.0-flash` |
| `ASSISTANT_NAME` | e.g. `In Vision` |
| `DATA_SOURCE` | `auto` (preferred) |
| `ALLOWED_ORIGINS` | Your Vercel URL(s), comma-separated, e.g. `https://your-app.vercel.app` |

4. Deploy. Smoke-test: open the Railway public URL — you should see health JSON (`{"status":"Rangeland Advisor API running"}`).
5. Also try `GET /health/data` to confirm Supabase + Gemini status.

Start command (already in config):

```bash
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Processed CSVs under `backend/data/processed/` ship in git, so the API can fall back if Supabase is briefly unreachable.

### 3. Vercel (frontend)

1. New project → same repo.
2. Set **Root Directory** to `frontend/`.
3. Build: `npm run build` · Output: `dist` (Vite defaults).
4. Env:

| Variable | Notes |
|----------|--------|
| `VITE_API_BASE_URL` | Railway public URL, **no trailing slash** |
| `VITE_SUPABASE_URL` | Optional — same as backend URL |
| `VITE_SUPABASE_ANON_KEY` | Optional — browser anon key only |

5. Redeploy after setting `VITE_API_BASE_URL` (Vite bakes env at build time).
6. Add the Vercel URL to Railway `ALLOWED_ORIGINS`, then redeploy Railway if needed.

[`frontend/vercel.json`](frontend/vercel.json) rewrites SPA routes to `index.html`.

### 4. Smoke checklist

- [ ] Railway `GET /` returns health JSON
- [ ] Vercel loads the Farmar UI
- [ ] Ask tab → `POST /chat` succeeds (Network tab)
- [ ] No CORS errors in the browser console
- [ ] Profile login works against Supabase `users` (if configured)

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

## Frontend (local)

```bash
cd frontend
cp .env.example .env   # VITE_API_BASE_URL=http://localhost:8000
npm.cmd install        # use npm.cmd on Windows if PowerShell blocks npm
npm.cmd run dev
```

See `frontend/README.md` and `frontend/API.md` for UI to API wiring.

## Backend docs

See `BACKEND_STATUS.md` for phases, endpoints, and tool design.
