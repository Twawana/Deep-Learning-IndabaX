export const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const NAMIBIA_LOCATIONS = [
  { name: "Gobabis", region: "Omaheke", lat: -22.45, lon: 18.97 },
  { name: "Windhoek", region: "Khomas", lat: -22.57, lon: 17.08 },
  { name: "Otjiwarongo", region: "Otjozondjupa", lat: -20.46, lon: 16.65 },
  { name: "Outjo", region: "Kunene", lat: -20.12, lon: 16.15 },
  { name: "Keetmanshoop", region: "ǁKaras", lat: -26.58, lon: 18.13 },
  { name: "Katima Mulilo", region: "Zambezi", lat: -17.5, lon: 24.27 },
  { name: "Neudamm", region: "Khomas", lat: -22.5, lon: 17.37 },
  { name: "Molly", region: "Omaheke", lat: -22.46, lon: 19.75 },
  { name: "Cala", region: "Omaheke", lat: -21.41, lon: 18.33 },
  { name: "Ghaub", region: "Otjozondjupa", lat: -19.45, lon: 17.78 },
  { name: "Okongo", region: "Ohangwena", lat: -17.52, lon: 17.77 },
  { name: "Oshakati", region: "Oshana", lat: -17.78, lon: 15.7 },
  { name: "Swakopmund", region: "Erongo", lat: -22.68, lon: 14.53 },
  { name: "Rundu", region: "Kavango East", lat: -17.93, lon: 19.77 },
  { name: "Mariental", region: "Hardap", lat: -24.63, lon: 17.97 },
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
  "Can my cattle stay here another week?",
  "How is pasture looking around Gobabis?",
  "Will rainfall help my grazing situation?",
];

export const DEFAULT_FARM_CONTEXT = {
  farmerName: "",
  farmName: "",
  phone: "",
  location: "Gobabis",
  region: "Omaheke",
  village: "",
  customLocation: "",
  lat: -22.45,
  lon: 18.97,
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
