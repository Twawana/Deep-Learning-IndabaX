export const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

/**
 * Only towns/sites that resolve in the processed Lacuna advisory dataset
 * (exact site or PLACE_ALIASES on the backend).
 */
export const NAMIBIA_LOCATIONS = [
  { name: "Gobabis", region: "Omaheke", lat: -22.45, lon: 18.97, mapsTo: "Molly", supported: true },
  { name: "Molly", region: "Central Kalahari", lat: -22.46, lon: 19.75, mapsTo: "Molly", supported: true },
  { name: "Cala", region: "Central Kalahari", lat: -21.41, lon: 18.33, mapsTo: "Cala", supported: true },
  { name: "Windhoek", region: "Khomas", lat: -22.57, lon: 17.08, mapsTo: "Neudamm", supported: true },
  { name: "Neudamm", region: "Highland shrubland", lat: -22.5, lon: 17.37, mapsTo: "Neudamm", supported: true },
  { name: "Otjiwarongo", region: "Otjozondjupa", lat: -20.46, lon: 16.65, mapsTo: "Lardner", supported: true },
  { name: "Outjo", region: "Kunene", lat: -20.12, lon: 16.15, mapsTo: "Ghaub", supported: true },
  { name: "Ghaub", region: "Karstveld", lat: -19.45, lon: 17.78, mapsTo: "Ghaub", supported: true },
  { name: "Keetmanshoop", region: "ǁKaras", lat: -26.58, lon: 18.13, mapsTo: "Keetmanshop", supported: true },
  { name: "Katima Mulilo", region: "Zambezi", lat: -17.5, lon: 24.27, mapsTo: "Katima Mulilo Quarantine Station", supported: true },
  { name: "Okongo", region: "Ohangwena", lat: -17.52, lon: 17.77, mapsTo: "Okongo", supported: true },
  { name: "Agagia", region: "Thornbush shrubland", lat: -21.56, lon: 17.25, mapsTo: "Agagia", supported: true },
  { name: "Beulah", region: "Karstveld", lat: -19.63, lon: 14.89, mapsTo: "Beulah", supported: true },
  { name: "Lardner", region: "Thornbush shrubland", lat: -19.98, lon: 17.03, mapsTo: "Lardner", supported: true },
  { name: "Ogongo", region: "Cuvelai/Western Kalahari", lat: -17.68, lon: 15.31, mapsTo: "Ogongo", supported: true },
  { name: "Okahambo", region: "Northern Kalahari", lat: -20.86, lon: 19.23, mapsTo: "Okahambo", supported: true },
  { name: "Okarandu", region: "Western highland", lat: -21.34, lon: 15.59, mapsTo: "Okarandu", supported: true },
  { name: "Onamundidi", region: "Northeastern Kalahari woodland/Cuvelai", lat: -17.51, lon: 16.56, mapsTo: "Onamundidi", supported: true },
  { name: "Olifantswater West", region: "Southern Kalahari", lat: -23.66, lon: 18.37, mapsTo: "Olifantswater West", supported: true },
  { name: "Suederecke", region: "Dwarf Shrub Savvanah", lat: -25.64, lon: 17.3, mapsTo: "Suederecke", supported: true },
  { name: "Tiras", region: "Desert - Dwarf Shrub Transition", lat: -26.14, lon: 16.57, mapsTo: "Tiras", supported: true },
  { name: "Uukolonkadhi", region: "Western highland/Western Kalahari", lat: -17.66, lon: 14.31, mapsTo: "Uukolonkadhi", supported: true },
  { name: "Buschpfanne", region: "Dwarf shrub-southern Kalahari transition", lat: -26.84, lon: 19.78, mapsTo: "Buschpfanne", supported: true },
];

/** Unsupported picker entries kept only for messaging / future aliases */
export const UNSUPPORTED_LOCATIONS = [
  "Oshakati",
  "Swakopmund",
  "Rundu",
  "Mariental",
  "Tsumeb",
  "Grootfontein",
  "Walvis Bay",
  "Okahandja",
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

/** Dataset lookup key: always the selected town/site, never free-text notes. */
export function datasetLocation(farm) {
  return (farm?.location || "").trim();
}
