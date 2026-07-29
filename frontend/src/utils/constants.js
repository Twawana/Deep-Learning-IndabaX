export const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

export const NAMIBIA_LOCATIONS = [
  { name: "Windhoek", region: "Khomas", lat: -22.57, lon: 17.08 },
  { name: "Oshakati", region: "Oshana", lat: -17.78, lon: 15.7 },
  { name: "Swakopmund", region: "Erongo", lat: -22.68, lon: 14.53 },
  { name: "Rundu", region: "Kavango East", lat: -17.93, lon: 19.77 },
  { name: "Katima Mulilo", region: "Zambezi", lat: -17.5, lon: 24.27 },
  { name: "Otjiwarongo", region: "Otjozondjupa", lat: -20.46, lon: 16.65 },
  { name: "Keetmanshoop", region: "ǁKaras", lat: -26.58, lon: 18.13 },
  { name: "Gobabis", region: "Omaheke", lat: -22.45, lon: 18.97 },
  { name: "Mariental", region: "Hardap", lat: -24.63, lon: 17.97 },
  { name: "Outjo", region: "Kunene", lat: -20.12, lon: 16.15 },
  { name: "Tsumeb", region: "Oshikoto", lat: -19.25, lon: 17.72 },
  { name: "Grootfontein", region: "Otjozondjupa", lat: -19.57, lon: 18.12 },
  { name: "Walvis Bay", region: "Erongo", lat: -22.96, lon: 14.51 },
  { name: "Okahandja", region: "Otjozondjupa", lat: -21.98, lon: 16.91 },
];

export const LAND_TENURE_OPTIONS = [
  { value: "communal", label: "Communal" },
  { value: "commercial", label: "Commercial" },
  { value: "conservancy", label: "Conservancy" },
  { value: "unknown", label: "Prefer not to say" },
];

export const LIVESTOCK_OPTIONS = [
  { value: "cattle", label: "Cattle" },
  { value: "goats", label: "Goats" },
  { value: "sheep", label: "Sheep" },
  { value: "mixed", label: "Mixed herd" },
  { value: "other", label: "Other" },
];

export const WATER_SOURCE_OPTIONS = [
  { value: "borehole", label: "Borehole" },
  { value: "dam", label: "Dam / pond" },
  { value: "river", label: "River / stream" },
  { value: "pipeline", label: "Pipeline / tap" },
  { value: "rainwater", label: "Rainwater" },
  { value: "mixed", label: "More than one" },
  { value: "unknown", label: "Not sure" },
];

export const CHAT_SUGGESTIONS = [
  "Is this camp overgrazed?",
  "What's a safe stocking rate right now?",
  "Should I move my herd?",
];

export const DEFAULT_FARM_CONTEXT = {
  farmerName: "",
  farmName: "",
  phone: "",
  location: "Windhoek",
  region: "Khomas",
  village: "",
  customLocation: "",
  lat: -22.57,
  lon: 17.08,
  herdSize: 50,
  livestockType: "cattle",
  campName: "",
  numberOfCamps: "",
  farmSizeHa: "",
  landTenure: "communal",
  waterSource: "borehole",
  farmNotes: "",
};

export const FARM_STORAGE_KEY = "farmar-profile-v2";

