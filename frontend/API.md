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
  "farmer_name": "Maria",
  "farm_name": "Green Valley",
  "phone": "0812345678",
  "location": "20km east of Otjiwarongo",
  "nearest_town": "Otjiwarongo",
  "region": "Otjozondjupa",
  "village": "Okakarara",
  "herd_size": 80,
  "livestock_type": "cattle",
  "camp_name": "North camp",
  "number_of_camps": 4,
  "farm_size_ha": 2500,
  "land_tenure": "communal",
  "water_source": "borehole",
  "farm_notes": "Bush encroachment on south camp",
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

## 3. Pasture analysis (preferred for Pasture tab)

### `GET /pasture/analysis`

Used by the Pasture screen. Pass farm context as query params:

`location`, `nearest_town`, `region`, `camp_name`, `herd_size`, `livestock_type`, `village`, `farm_notes`, `lat`, `lon`, `days`

**Response**
```json
{
  "location_label": "Otjozondjupa — Camp A",
  "region": "Otjozondjupa",
  "camp_name": "Camp A",
  "nearest_town": "Otjiwarongo",
  "health": {
    "score": 72,
    "status": "Good Condition",
    "explanation": "Vegetation is healthy, but grazing pressure should be monitored."
  },
  "vegetation": {
    "ndvi": 0.48,
    "grass_cover": "65%",
    "grass_biomass": "Medium",
    "bush_encroachment": "Low/Medium"
  },
  "grazing": {
    "pressure": "High",
    "herd_size": 120,
    "livestock_type": "cattle",
    "recommended_capacity": 80,
    "warning": "Your livestock numbers are above the estimated carrying capacity."
  },
  "weather_impact": {
    "rainfall_last_30_days": 18,
    "average_rainfall": 45,
    "status": "Below normal",
    "explanation": "Less rain than usual means grass recovers more slowly."
  },
  "ai_advice": "Based on high grazing pressure and below-average rainfall, consider moving part of your herd to another camp within 2 weeks."
}
```

If this endpoint is missing, the frontend falls back to `GET /pasture` + `GET /weather`.

### `GET /pasture?location=Windhoek&region=Khomas&camp_name=Camp%20A`

Fallback / raw dataset fields:

```json
{
  "location": "Windhoek",
  "region": "Khomas",
  "condition": "Good Condition",
  "health_score": 72,
  "summary": "Vegetation is healthy, but grazing pressure should be monitored.",
  "ndvi": 0.48,
  "grass_cover": "65%",
  "vegetation_cover": "65%",
  "grass_biomass": "Medium",
  "bush_encroachment": "Low/Medium",
  "grazing_pressure": "High",
  "carrying_capacity": 80,
  "recommended_capacity": 80,
  "ai_advice": "Consider moving part of your herd within 2 weeks."
}
```

### `GET /rangeland?location=…&region=…`

Same purpose as `/pasture` (explicit dataset query). Same shape is fine.

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
  "rainfall_last_30_days": 18,
  "average_rainfall": 45,
  "average_rainfall_30_days": 45,
  "drought_indicator": "Below normal",
  "rainfall_status": "Below normal",
  "rainfall_explanation": "Less rain than usual means grass recovers more slowly.",
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
