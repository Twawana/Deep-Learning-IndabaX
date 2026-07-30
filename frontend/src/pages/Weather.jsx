import Card from "../components/Card";
import ErrorAlert from "../components/ErrorAlert";
import Loader from "../components/Loader";
import { useFarmContext } from "../context/FarmContext";
import { useWeather } from "../hooks/useWeather";
import { NAMIBIA_LOCATIONS, datasetLocation } from "../utils/constants";
import { formatValue, toArray } from "../utils/format";

const KEYS = [
  { key: "temperature", label: "Temperature" },
  { key: "rainfall", label: "Near-term rain" },
  { key: "rainfall_last_7_days", label: "Recent rain total" },
  { key: "forecast_total_mm", label: "Forecast rain total" },
  { key: "source", label: "Source" },
  { key: "confidence", label: "Confidence" },
];

export default function Weather() {
  const farm = useFarmContext();
  const { data, isLoading, error, fetchWeather, setError } = useWeather();

  const handleSubmit = (event) => {
    event.preventDefault();
    const location = datasetLocation(farm);
    if (!location) {
      setError("Select a supported town or research site.");
      return;
    }
    fetchWeather(farm.lat, farm.lon, {
      days: 7,
      location,
      region: farm.region,
    });
  };

  const rows = data
    ? KEYS.filter(({ key }) => data[key] != null && data[key] !== "")
    : [];

  const limitations = toArray(data?.limitations);

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="space-y-3">
        <select
          aria-label="Location"
          value={farm.location}
          onChange={(e) => farm.setLocationByName(e.target.value)}
          className="w-full rounded-xl border border-veld-200 bg-white px-3.5 py-3 text-sm font-medium outline-none focus:border-veld-500"
        >
          {NAMIBIA_LOCATIONS.map((loc) => (
            <option key={loc.name} value={loc.name}>
              {loc.name}
              {loc.mapsTo && loc.mapsTo !== loc.name ? ` → ${loc.mapsTo}` : ""}
            </option>
          ))}
        </select>
        <button
          type="submit"
          disabled={isLoading}
          className="flex w-full items-center justify-center rounded-xl bg-veld-800 py-3.5 text-sm font-semibold text-white active:bg-veld-900 disabled:opacity-60"
        >
          {isLoading ? "Loading…" : "Check weather"}
        </button>
      </form>

      {error && (
        <ErrorAlert message={error} onDismiss={() => setError(null)} />
      )}

      {isLoading && <Loader label="Loading…" />}

      {!isLoading && data && (
        <>
          <Card title={data.match_value || farm.location}>
            {rows.length ? (
              <dl className="space-y-3">
                {rows.map(({ key, label }) => (
                  <div key={key} className="flex justify-between gap-3">
                    <dt className="text-sm text-ink-muted">{label}</dt>
                    <dd className="text-right text-sm font-semibold text-veld-900">
                      {formatValue(data[key])}
                      {key === "forecast_total_mm" && typeof data[key] === "number"
                        ? " mm"
                        : ""}
                    </dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="text-sm text-ink-muted">No weather details yet</p>
            )}
          </Card>

          {limitations.length > 0 && (
            <Card title="Data limitations">
              <ul className="space-y-2">
                {limitations.map((item, i) => (
                  <li key={i} className="text-sm text-ink-muted">
                    {item}
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
