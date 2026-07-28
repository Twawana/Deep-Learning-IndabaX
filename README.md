# Farmar

AI-powered rangeland and pasture advisory frontend for Namibian livestock farmers. Built for the Deep Learning IndabaX Namibia 2026 Hackathon.

## Stack

- React (Vite)
- Tailwind CSS v4
- Axios
- React Router
- TanStack React Query

## Setup

```bash
npm install
cp .env.example .env
npm run dev
```

The app expects the backend API at `http://localhost:8000/api` by default. Override with:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

## Pages

| Route       | Description                                      |
|-------------|--------------------------------------------------|
| `/`         | Dashboard — weather, pasture, alerts, tips       |
| `/chat`     | Conversational AI advisor                        |
| `/pasture`  | Pasture condition by location                    |
| `/weather`  | Weather by lat/lon or Namibian town              |

## API endpoints used

- `GET /dashboard`
- `POST /chat`
- `GET /pasture?location=`
- `GET /weather?lat=&lon=`
