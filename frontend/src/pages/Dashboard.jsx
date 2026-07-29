import { Link } from "react-router-dom";
import Card from "../components/Card";
import ErrorAlert from "../components/ErrorAlert";
import Loader from "../components/Loader";
import { useDashboard } from "../hooks/useDashboard";
import { useFarmContext } from "../context/FarmContext";
import { formatLabel, formatValue, toArray } from "../utils/format";
import { NAMIBIA_LOCATIONS } from "../utils/constants";

const WEATHER_KEYS = ["temperature", "rainfall", "rainfall_last_30_days", "forecast_total_mm", "source"];
const PASTURE_KEYS = ["vegetation_cover", "bush_encroachment", "biomass", "grazing_pressure", "observation_date", "confidence"];

function pickEntries(data, keys) {
  if (!data || typeof data !== "object") return [];
  const preferred = keys
    .filter((k) => data[k] != null && data[k] !== "")
    .map((k) => [k, data[k]]);
  if (preferred.length) return preferred;
  return Object.entries(data).slice(0, 4);
}

function SimpleMetrics({ data, keys }) {
  const entries = pickEntries(data, keys);
  if (!entries.length) {
    return <p className="text-sm text-ink-muted">No data yet</p>;
  }
  return (
    <dl className="space-y-2.5">
      {entries.map(([key, value]) => (
        <div key={key} className="flex justify-between gap-3">
          <dt className="text-sm text-ink-muted">{formatLabel(key)}</dt>
          <dd className="text-sm font-semibold text-veld-900">
            {formatValue(value)}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function SimpleList({ items, empty }) {
  const list = toArray(items);
  if (!list.length) return <p className="text-sm text-ink-muted">{empty}</p>;
  return (
    <ul className="space-y-2">
      {list.slice(0, 5).map((item, i) => (
        <li key={i} className="text-sm text-ink">
          {typeof item === "string" ? item : formatValue(item)}
        </li>
      ))}
    </ul>
  );
}

export default function Dashboard() {
  const farm = useFarmContext();
  const { data, isLoading, error, refetch, isFetching } = useDashboard();

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <select
          aria-label="Location"
          value={farm.location}
          onChange={(e) => farm.setLocationByName(e.target.value)}
          className="min-w-0 flex-1 rounded-xl border border-veld-200 bg-white px-3 py-2.5 text-sm font-medium outline-none focus:border-veld-500"
        >
          {NAMIBIA_LOCATIONS.map((loc) => (
            <option key={loc.name} value={loc.name}>
              {loc.name}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          className="rounded-xl border border-veld-200 bg-white px-3 py-2.5 text-sm font-semibold text-veld-800 disabled:opacity-50"
        >
          {isFetching ? "…" : "Refresh"}
        </button>
      </div>

      <Link
        to="/chat"
        className="flex w-full items-center justify-center rounded-xl bg-veld-800 py-3.5 text-sm font-semibold text-white active:bg-veld-900"
      >
        Ask for advice
      </Link>

      {error && <ErrorAlert message={error} />}

      {isLoading ? (
        <Loader label="Loading…" />
      ) : data ? (
        <div className="space-y-3">
          <Card title="Weather">
            <SimpleMetrics data={data.weather} keys={WEATHER_KEYS} />
          </Card>
          <Card title="Pasture">
            <SimpleMetrics data={data.pasture_status} keys={PASTURE_KEYS} />
          </Card>
          {toArray(data.alerts).length > 0 && (
            <Card title="Alerts">
              <SimpleList items={data.alerts} empty="" />
            </Card>
          )}
          {toArray(data.recommendations).length > 0 && (
            <Card title="Tips">
              <SimpleList items={data.recommendations} empty="" />
            </Card>
          )}
        </div>
      ) : null}
    </div>
  );
}
