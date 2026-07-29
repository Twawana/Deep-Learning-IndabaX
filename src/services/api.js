/**
 * Farmar API client — frontend contract for the agent backend.
 * Backend is expected to implement these routes under API_BASE.
 */
import axios from "axios";
import { API_BASE } from "../utils/constants";

const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
  timeout: 60000,
});

/**
 * GET /dashboard
 * Overview for the home screen.
 */
export async function getDashboard(params = {}) {
  const { data } = await api.get("/dashboard", { params });
  return data;
}

/**
 * POST /chat  — main agentic advisor endpoint
 *
 * Request body:
 * {
 *   message: string,
 *   location: string,
 *   region?: string,
 *   herd_size?: number,
 *   camp_name?: string,
 *   land_tenure?: "communal" | "commercial" | "conservancy" | "unknown",
 *   lat?: number,
 *   lon?: number,
 *   history?: { role: "user"|"assistant", content: string }[]
 * }
 *
 * Expected response:
 * {
 *   response: string,                 // plain-language advice
 *   reasoning: string,                // why (tools + data), not just a verdict
 *   recommendations: string[],
 *   tools_used: [{ name, summary, input? }],  // e.g. query_rangeland, fetch_weather
 *   sources?: { pasture?: object, weather?: object },
 *   limitations?: string
 * }
 */
export async function sendMessage(payload) {
  const { data } = await api.post("/chat", payload);
  return data;
}

/**
 * GET /pasture?location=&region=
 * Query rangeland / pasture dataset for a location.
 *
 * Expected response fields (subset OK):
 * soil_quality, grass_type, condition, ndvi, vegetation_cover,
 * grass_biomass, bush_biomass, bush_encroachment, livestock_density,
 * carrying_capacity, grazing_pressure, browsing_pressure, land_tenure, region
 */
export async function getPasture(location, extra = {}) {
  const { data } = await api.get("/pasture", {
    params: { location, ...extra },
  });
  return data;
}

/**
 * GET /rangeland?location=&region=
 * Explicit dataset query (agent tool mirror for the UI).
 */
export async function getRangeland(location, extra = {}) {
  const { data } = await api.get("/rangeland", {
    params: { location, ...extra },
  });
  return data;
}

/**
 * GET /weather?lat=&lon=&days=
 * Live weather / rainfall (backend should call Open-Meteo or NASA POWER).
 *
 * Expected response:
 * temperature, rainfall, humidity, recent_rainfall_mm,
 * rainfall_last_30_days, drought_indicator, source, forecast?
 */
export async function getWeather(lat, lon, extra = {}) {
  const { data } = await api.get("/weather", {
    params: { lat, lon, days: extra.days ?? 30, ...extra },
  });
  return data;
}

/**
 * GET /regions
 * Optional helper for location pickers.
 */
export async function getRegions() {
  const { data } = await api.get("/regions");
  return data;
}

export default api;
