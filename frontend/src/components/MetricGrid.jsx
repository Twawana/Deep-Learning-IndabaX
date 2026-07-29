import { formatLabel, formatValue } from "../utils/format";

const PASTURE_FIELDS = [
  "soil_quality",
  "grass_type",
  "condition",
  "ndvi",
  "vegetation_cover",
  "grass_biomass",
  "bush_biomass",
  "bush_encroachment",
  "livestock_density",
  "carrying_capacity",
  "grazing_pressure",
  "browsing_pressure",
  "land_tenure",
  "region",
];

const WEATHER_FIELDS = [
  "temperature",
  "rainfall",
  "humidity",
  "recent_rainfall_mm",
  "rainfall_last_30_days",
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
