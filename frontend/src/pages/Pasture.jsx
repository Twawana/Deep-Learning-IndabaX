import Card from "../components/Card";
import ErrorAlert from "../components/ErrorAlert";
import Loader from "../components/Loader";
import { useFarmContext } from "../context/FarmContext";
import { usePasture } from "../hooks/usePasture";
import { NAMIBIA_LOCATIONS } from "../utils/constants";
import { formatLabel, formatValue } from "../utils/format";

const KEY_FIELDS = [
  "condition",
  "soil_quality",
  "grass_type",
  "grazing_pressure",
  "carrying_capacity",
  "bush_encroachment",
];

export default function Pasture() {
  const farm = useFarmContext();
  const { data, isLoading, error, fetchPasture, setError } = usePasture();

  const handleSubmit = (event) => {
    event.preventDefault();
    fetchPasture(farm.location, { region: farm.region });
  };

  const entries = data
    ? KEY_FIELDS.filter((k) => data[k] != null && data[k] !== "").map((k) => [
        k,
        data[k],
      ])
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
          {isLoading ? "Loading…" : "Check pasture"}
        </button>
      </form>

      {error && (
        <ErrorAlert message={error} onDismiss={() => setError(null)} />
      )}

      {isLoading && <Loader label="Loading…" />}

      {!isLoading && data && (
        <Card title={farm.location}>
          {entries.length ? (
            <dl className="space-y-3">
              {entries.map(([key, value]) => (
                <div key={key} className="flex justify-between gap-3">
                  <dt className="text-sm text-ink-muted">{formatLabel(key)}</dt>
                  <dd className="text-right text-sm font-semibold text-veld-900">
                    {formatValue(value)}
                  </dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="text-sm text-ink-muted">No pasture details yet</p>
          )}
        </Card>
      )}
    </div>
  );
}
