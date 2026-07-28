import axios from "axios";
import { API_BASE } from "../utils/constants";

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
});

export async function getDashboard() {
  const { data } = await api.get("/dashboard");
  return data;
}

export async function sendMessage(message, location) {
  const { data } = await api.post("/chat", { message, location });
  return data;
}

export async function getPasture(location) {
  const { data } = await api.get("/pasture", {
    params: { location },
  });
  return data;
}

export async function getWeather(lat, lon) {
  const { data } = await api.get("/weather", {
    params: { lat, lon },
  });
  return data;
}

export default api;
