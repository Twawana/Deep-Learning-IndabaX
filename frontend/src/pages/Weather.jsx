import Card from "../components/Card";
import ErrorAlert from "../components/ErrorAlert";
import Loader from "../components/Loader";
import { useFarmContext } from "../context/FarmContext";
import { useWeather } from "../hooks/useWeather";
import { NAMIBIA_LOCATIONS } from "../utils/constants";
import { formatValue } from "../utils/format";

const KEYS = [
  { key: "temperature", label: "Temperature" },
  { key: "rainfall", label: "Rainfall" },
  { key: "humidity", label: "Humidity" },
  { key: "rainfall_last_30_days", label: "Last 30 days rain" },
  { key: "drought_indicator", label: "Drought" },
];

export default function Weather() {
  const farm = useFarmContext();
  const { data, isLoading, error, fetchWeather, setError } = useWeather();

  const handleSubmit = (event) => {
    event.preventDefault();
    fetchWeather(farm.lat, farm.lon, { days: 30 });
  };

  const rows = data
    ? KEYS.filter(({ key }) => data[key] != null && data[key] !== "")
    : [];

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
        <Card title={farm.location}>
          {rows.length ? (
            <dl className="space-y-3">
              {rows.map(({ key, label }) => (
                <div key={key} className="flex justify-between gap-3">
                  <dt className="text-sm text-ink-muted">{label}</dt>
                  <dd className="text-right text-sm font-semibold text-veld-900">
                    {formatValue(data[key])}
                  </dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="text-sm text-ink-muted">No weather details yet</p>
          )}
        </Card>
      )}
    </div>
  );
}
