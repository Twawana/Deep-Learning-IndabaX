/**
 * Farmar API client — wired to the IndabaX FastAPI backend.
 *
 * Backend base: http://localhost:8000 (no /api prefix)
 * Core routes: /pasture/{region}, /weather/{region}, /advisor, /chat, /dashboard
 */
import axios from "axios";
import { API_BASE } from "../utils/constants";

const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
  timeout: 60000,
});

function encodeRegion(location) {
  return encodeURIComponent(String(location || "").trim());
}

/**
 * GET /dashboard?location=&region=&lat=&lon=&herd_size=
 */
export async function getDashboard(params = {}) {
  const { data } = await api.get("/dashboard", { params });
  return data;
}

/**
 * POST /chat — Ask tab (tool-backed summary until Gemini is integrated)
 */
export async function sendMessage(payload) {
  const { data } = await api.post("/chat", payload);
  return data;
}

/**
 * GET /pasture/{region}
 * Normalizes backend PastureResponse into flat fields used by Pasture / Dashboard UI.
 */
export async function getPasture(location, extra = {}) {
  const region = location || extra.region;
  const { data } = await api.get(`/pasture/${encodeRegion(region)}`, {
    params: {
      include_history: extra.include_history || false,
    },
  });

  if (!data?.found) {
    const err = new Error(data?.message || "Region not found");
    err.response = { data };
    throw err;
  }

  const metrics = data.pasture || {};
  return {
    ...data,
    location: data.location,
    region: data.match_value || extra.region,
    vegetation_cover: metrics.vegetation_cover,
    bush_encroachment: metrics.bush_encroachment,
    biomass: metrics.biomass,
    grass_biomass: metrics.biomass,
    cover_perennial_grass_pct: metrics.cover_perennial_grass_pct,
    cover_annual_grass_pct: metrics.cover_annual_grass_pct,
    cover_bare_ground_pct: metrics.cover_bare_ground_pct,
    grazing_pressure: metrics.grazing_pressure_recorded,
    observation_date: data.observation_date,
    confidence: data.confidence,
    limitations: data.limitations || [],
    sites: data.sites || [],
    // Fields not in dataset — keep explicit nulls so UI does not invent them
    condition: null,
    soil_quality: null,
    grass_type: null,
    carrying_capacity: null,
    ndvi: null,
  };
}

/**
 * GET /rangeland — alias of pasture for older frontend docs
 */
export async function getRangeland(location, extra = {}) {
  return getPasture(location, extra);
}

/**
 * GET /weather/{region}
 * Prefers location/region name (backend resolves coordinates from dataset).
 * Falls back to nearest_town / location query param if lat/lon-only callers pass extras.location.
 */
export async function getWeather(lat, lon, extra = {}) {
  const region = (
    extra.location ||
    extra.nearest_town ||
    extra.region ||
    ""
  ).trim();

  // Never invent a town. Backend weather resolves coordinates from the dataset.
  if (!region) {
    const err = new Error(
      "Weather requires a supported town or research site."
    );
    throw err;
  }

  const pastDays = extra.past_days ?? 7;
  const { data } = await api.get(`/weather/${encodeRegion(region)}`, {
    params: {
      forecast_days: extra.forecast_days ?? Math.min(Number(extra.days) || 7, 16),
      past_days: pastDays,
    },
  });

  if (!data?.found) {
    const err = new Error(data?.message || "Region not found");
    err.response = { data };
    throw err;
  }

  const forecastDaily = data.forecast?.daily || [];
  const today = forecastDaily[0] || {};
  const recentDays = data.recent_rainfall?.days ?? pastDays;
  const recentTotal = data.recent_rainfall?.total_precipitation_mm;
  const forecastTotal = data.forecast?.total_precipitation_mm;

  let temperature = null;
  if (today.temperature_max_c != null && today.temperature_min_c != null) {
    temperature = `${Math.round(today.temperature_min_c)}-${Math.round(today.temperature_max_c)}C`;
  } else if (today.temperature_max_c != null) {
    temperature = `${Math.round(today.temperature_max_c)}C`;
  }

  const precipToday = today.precipitation_mm;
  const rainfall =
    precipToday == null ? null : `${precipToday} mm (near-term)`;
  const recentLabel =
    recentTotal == null ? null : `${recentTotal} mm (last ${recentDays} days)`;

  return {
    ...data,
    temperature,
    rainfall,
    humidity: null,
    recent_rainfall_mm: recentTotal,
    rainfall_recent: recentLabel,
    // Honest alias — value is the Open-Meteo recent window (default 7 days), not 30.
    rainfall_last_7_days: recentLabel,
    forecast_total_mm: forecastTotal,
    drought_indicator: null,
    source: data.source || "open-meteo",
    forecast: forecastDaily,
    confidence: data.confidence,
    limitations: data.limitations || [],
    // preserve raw coords from backend (dataset), not the phone GPS
    lat: data.latitude,
    lon: data.longitude,
  };
}

/**
 * GET /sites — research sites from processed dataset
 */
export async function getRegions() {
  const { data } = await api.get("/sites");
  const sites = data?.sites || [];
  return {
    regions: [...new Set(sites.map((s) => s.region).filter(Boolean))],
    sites,
  };
}

/**
 * POST /advisor — raw context package (optional advanced use)
 */
export async function getAdvisorContext(payload) {
  const { data } = await api.post("/advisor", payload);
  return data;
}

export async function getAdminState() {
  const { data } = await api.get("/admin/state");
  return data;
}

export async function loginAdmin(passcode) {
  const { data } = await api.post("/admin/login", { passcode });
  return data;
}

export async function switchAccount(userId) {
  const { data } = await api.post("/admin/switch", { user_id: userId });
  return data;
}

export async function logoutAccount() {
  const { data } = await api.post("/admin/logout");
  return data;
}

export async function createUser(payload) {
  const { data } = await api.post("/admin/users", payload);
  return data;
}

export async function patchUser(userId, patch) {
  const { data } = await api.patch(`/admin/users/${encodeURIComponent(userId)}`, patch);
  return data;
}

export async function deleteUser(userId) {
  const { data } = await api.delete(`/admin/users/${encodeURIComponent(userId)}`);
  return data;
}

export async function patchAdminSettings(patch) {
  const { data } = await api.patch("/admin/settings", patch);
  return data;
}

export default api;
