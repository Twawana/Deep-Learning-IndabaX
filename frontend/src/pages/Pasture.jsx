import Card from "../components/Card";
import ErrorAlert from "../components/ErrorAlert";
import Loader from "../components/Loader";
import { useFarmContext } from "../context/FarmContext";
import { usePasture } from "../hooks/usePasture";
import { NAMIBIA_LOCATIONS, datasetLocation } from "../utils/constants";
import { formatLabel, formatValue, toArray } from "../utils/format";

const KEY_FIELDS = [
  "vegetation_cover",
  "bush_encroachment",
  "biomass",
  "cover_perennial_grass_pct",
  "cover_bare_ground_pct",
  "grazing_pressure",
  "observation_date",
  "confidence",
];

export default function Pasture() {
  const farm = useFarmContext();
  const { data, isLoading, error, fetchPasture, setError } = usePasture();

  const handleSubmit = (event) => {
    event.preventDefault();
    const location = datasetLocation(farm);
    if (!location) {
      setError("Select a supported town or research site.");
      return;
    }
    fetchPasture(location, { region: farm.region });
  };

  const entries = data
    ? KEY_FIELDS.filter((k) => data[k] != null && data[k] !== "").map((k) => [
        k,
        data[k],
      ])
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
          {isLoading ? "Loading…" : "Check pasture"}
        </button>
      </form>

      {error && (
        <ErrorAlert message={error} onDismiss={() => setError(null)} />
      )}

      {isLoading && <Loader label="Loading…" />}

      {!isLoading && data && (
        <>
          <Card title={data.match_value || farm.location}>
            {data.sites?.length > 0 && (
              <p className="mb-3 text-xs text-ink-muted">
                Sites: {data.sites.join(", ")}
              </p>
            )}
            {entries.length ? (
              <dl className="space-y-3">
                {entries.map(([key, value]) => (
                  <div key={key} className="flex justify-between gap-3">
                    <dt className="text-sm text-ink-muted">{formatLabel(key)}</dt>
                    <dd className="text-right text-sm font-semibold text-veld-900">
                      {formatValue(value)}
                      {["vegetation_cover", "bush_encroachment", "cover_perennial_grass_pct", "cover_bare_ground_pct"].includes(key) && typeof value === "number"
                        ? "%"
                        : ""}
                    </dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="text-sm text-ink-muted">No pasture details yet</p>
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
