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

export async function getDashboard(params = {}) {
  const { data } = await api.get("/dashboard", { params });
  return data;
}

export async function sendMessage(payload) {
  const { data } = await api.post("/chat", payload);
  return data;
}

/**
 * GET /pasture
 * Raw rangeland / pasture dataset fields for a location.
 */
export async function getPasture(location, extra = {}) {
  const { data } = await api.get("/pasture", {
    params: { location, ...extra },
  });
  return data;
}

/**
 * GET /pasture/analysis
 * Full pasture screen payload (preferred).
 *
 * Query params may include:
 * location, region, camp_name, herd_size, livestock_type, lat, lon, village, farm_notes
 */
export async function getPastureAnalysis(params = {}) {
  const { data } = await api.get("/pasture/analysis", { params });
  return data;
}

export async function getRangeland(location, extra = {}) {
  const { data } = await api.get("/rangeland", {
    params: { location, ...extra },
  });
  return data;
}

export async function getWeather(lat, lon, extra = {}) {
  const { data } = await api.get("/weather", {
    params: { lat, lon, days: extra.days ?? 30, ...extra },
  });
  return data;
}

export async function getRegions() {
  const { data } = await api.get("/regions");
  return data;
}

export default api;
