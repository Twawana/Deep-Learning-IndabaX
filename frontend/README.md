# Farmar (Mobile App)

AI-powered rangeland and pasture advisory **mobile app** for Namibian livestock farmers. Built for the Deep Learning IndabaX Namibia 2026 Hackathon.

## What the frontend covers

| Challenge requirement | Where in the app |
|---|---|
| Query rangeland/pasture by location | **Pasture** tab + agent tools via `/chat` |
| Live weather/rainfall (Open-Meteo / NASA POWER via backend) | **Weather** tab + agent tools via `/chat` |
| LLM agentic advice with reasoning | **Ask** tab — shows response, reasoning, tools used, sources |
| Conversational UI (location + herd size) | **Ask** tab — farm context bar |
| Speech-to-text / text-to-speech (bonus) | Mic button + **Listen** on AI replies (Web Speech API) |

Full backend request/response shapes: see [`API.md`](./API.md).

## Stack

- React (Vite) — mobile-first UI
- Tailwind CSS v4
- Axios + React Router + TanStack Query
- Capacitor — native Android / iOS shell
- Web Speech API — voice in / voice out

## Run

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

```env
VITE_API_BASE_URL=http://localhost:8000
```

Run the FastAPI backend first (`cd backend && uvicorn main:app --reload --port 8000`).

## Screens

| Tab | Route | Backend |
|-----|-------|---------|
| Home | `/` | `GET /dashboard` |
| Ask | `/chat` | `POST /chat` (tool-backed; Gemini later) |
| Pasture | `/pasture` | `GET /pasture/{region}` |
| Weather | `/weather` | `GET /weather/{region}` |
| Profile | `/profile` | Local profile (saved in browser) |

## Native builds

```bash
npm run mobile:android
npm run mobile:ios
```
