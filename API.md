# Farmar API Contract (Frontend → Backend)

Base URL: `http://localhost:8000/api` (override with `VITE_API_BASE_URL`)

The frontend does **not** call Open-Meteo / the CSV directly. Your agent backend should tool-call those sources and return the shaped responses below.

---

## 1. Agent chat (required)

### `POST /chat`

Farmer conversational interface. Backend should use an LLM with tool-calling to:
1. Query the rangeland/pasture dataset for the given location
2. Call a live weather/rainfall API (Open-Meteo or NASA POWER)
3. Combine both into plain-language advice with **reasoning**

**Request**
```json
{
  "message": "Is this camp overgrazed given my herd size?",
  "location": "Otjiwarongo",
  "region": "Otjozondjupa",
  "herd_size": 80,
  "camp_name": "North camp",
  "land_tenure": "communal",
  "lat": -20.46,
  "lon": 16.65,
  "history": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}
```

**Response**
```json
{
  "response": "Based on current grazing pressure and recent rainfall…",
  "reasoning": "I queried the rangeland dataset for Otjiwarongo and pulled 30-day rainfall from Open-Meteo. Grazing pressure is high (…); rainfall is below seasonal average (…), so carrying capacity is reduced.",
  "recommendations": [
    "Rest the north camp for 4–6 weeks",
    "Move ~30 animals to a rested paddock"
  ],
  "tools_used": [
    { "name": "query_rangeland", "summary": "Fetched pasture metrics for Otjiwarongo" },
    { "name": "fetch_weather", "summary": "Open-Meteo 30-day rainfall & drought signal" }
  ],
  "sources": {
    "pasture": { "grazing_pressure": "high", "carrying_capacity": "…" },
    "weather": { "rainfall_last_30_days": "12mm", "drought_indicator": "moderate" }
  },
  "limitations": "Estimate based on synthetic/regional data; verify on the ground."
}
```

---

## 2. Dashboard

### `GET /dashboard`

Optional query: `?location=Windhoek&lat=-22.57&lon=17.08`

```json
{
  "weather": {},
  "pasture_status": {},
  "alerts": [],
  "recommendations": []
}
```

---

## 3. Pasture / rangeland dataset

### `GET /pasture?location=Windhoek&region=Khomas`

```json
{
  "location": "Windhoek",
  "region": "Khomas",
  "soil_quality": "moderate",
  "grass_type": "perennial savannah",
  "condition": "fair",
  "ndvi": 0.42,
  "vegetation_cover": "45%",
  "grass_biomass": "…",
  "bush_biomass": "…",
  "bush_encroachment": "moderate",
  "livestock_density": "…",
  "carrying_capacity": "…",
  "grazing_pressure": "high",
  "browsing_pressure": "medium",
  "land_tenure": "communal"
}
```

### `GET /rangeland?location=…&region=…`

Same purpose as `/pasture` (explicit dataset query). Returning the same shape as `/pasture` is fine.

---

## 4. Live weather / rainfall

### `GET /weather?lat=-22.57&lon=17.08&days=30`

Backend should call **Open-Meteo** or **NASA POWER**.

```json
{
  "temperature": "24°C",
  "rainfall": "2mm (today)",
  "humidity": "35%",
  "recent_rainfall_mm": 18,
  "rainfall_last_30_days": "18mm",
  "drought_indicator": "moderate",
  "source": "Open-Meteo",
  "forecast": []
}
```

---

## 5. Optional

### `GET /regions`

```json
{
  "regions": ["Khomas", "Oshana", "Otjozondjupa", "..."]
}
```

---

## Voice (frontend-only)

Speech-to-text and text-to-speech run in the browser (Web Speech API). No backend voice endpoints are required.
