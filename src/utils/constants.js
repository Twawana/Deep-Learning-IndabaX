export const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

export const NAMIBIA_LOCATIONS = [
  { name: "Windhoek", lat: -22.57, lon: 17.08 },
  { name: "Oshakati", lat: -17.78, lon: 15.7 },
  { name: "Swakopmund", lat: -22.68, lon: 14.53 },
  { name: "Rundu", lat: -17.93, lon: 19.77 },
  { name: "Katima Mulilo", lat: -17.5, lon: 24.27 },
  { name: "Otjiwarongo", lat: -20.46, lon: 16.65 },
  { name: "Keetmanshoop", lat: -26.58, lon: 18.13 },
  { name: "Gobabis", lat: -22.45, lon: 18.97 },
  { name: "Mariental", lat: -24.63, lon: 17.97 },
  { name: "Outjo", lat: -20.12, lon: 16.15 },
  { name: "Tsumeb", lat: -19.25, lon: 17.72 },
  { name: "Grootfontein", lat: -19.57, lon: 18.12 },
  { name: "Walvis Bay", lat: -22.96, lon: 14.51 },
  { name: "Okahandja", lat: -21.98, lon: 16.91 },
];

export const CHAT_SUGGESTIONS = [
  "Is this camp currently overgrazed?",
  "What's a safe stocking rate for this area right now?",
  "Should I move my herd, and if so when?",
  "How does recent rainfall affect grazing capacity?",
];
