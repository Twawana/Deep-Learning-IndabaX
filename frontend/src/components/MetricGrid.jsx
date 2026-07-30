import { formatLabel, formatValue } from "../utils/format";

const PASTURE_FIELDS = [
  "vegetation_cover",
  "bush_encroachment",
  "biomass",
  "grass_biomass",
  "cover_perennial_grass_pct",
  "cover_bare_ground_pct",
  "grazing_pressure",
  "observation_date",
  "confidence",
  "condition",
  "soil_quality",
  "grass_type",
  "carrying_capacity",
  "ndvi",
  "region",
];

const WEATHER_FIELDS = [
  "temperature",
  "rainfall",
  "rainfall_last_7_days",
  "forecast_total_mm",
  "recent_rainfall_mm",
  "humidity",
  "drought_indicator",
  "source",
];

export function MetricGrid({ data, preferredKeys = [] }) {
  if (!data || typeof data !== "object") {
    return (
      <p className="text-sm text-ink-muted">No data returned from the API.</p>
    );
  }

  const keys =
    preferredKeys.length > 0
      ? preferredKeys.filter((key) => data[key] !== undefined && data[key] !== null && data[key] !== "")
      : Object.keys(data);

  const extraKeys = Object.keys(data).filter(
    (key) => !preferredKeys.includes(key) && !["location", "lat", "lon"].includes(key)
  );

  const displayKeys = preferredKeys.length
    ? [...keys, ...extraKeys.filter((k) => !keys.includes(k))]
    : keys;

  if (displayKeys.length === 0) {
    return (
      <p className="text-sm text-ink-muted">No data returned from the API.</p>
    );
  }

  return (
    <div className="space-y-2">
      {displayKeys.map((key) => (
        <div
          key={key}
          className="flex items-start justify-between gap-3 rounded-xl bg-veld-50 px-3 py-2.5"
        >
          <span className="text-sm text-ink-muted">{formatLabel(key)}</span>
          <span className="max-w-[55%] text-right text-sm font-semibold text-veld-900">
            {formatValue(data[key])}
          </span>
        </div>
      ))}
    </div>
  );
}

export { PASTURE_FIELDS, WEATHER_FIELDS };
