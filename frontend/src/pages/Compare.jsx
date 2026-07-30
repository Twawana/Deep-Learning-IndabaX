import { useState } from "react";
import Card from "../components/Card";
import ErrorAlert from "../components/ErrorAlert";
import Loader from "../components/Loader";
import ActionPriorityBanner from "../components/decision/ActionPriorityBanner";
import { useFarmContext } from "../context/FarmContext";
import { compareLocations } from "../services/api";
import { NAMIBIA_LOCATIONS } from "../utils/constants";
import { formatValue, getErrorMessage } from "../utils/format";

export default function Compare() {
  const farm = useFarmContext();
  const [locationA, setLocationA] = useState(farm.location || "Gobabis");
  const [locationB, setLocationB] = useState("Otjiwarongo");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showTech, setShowTech] = useState(false);

  const handleCompare = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await compareLocations(locationA, locationB, {
        land_tenure: farm.landTenure,
        herd_size: farm.herdSize ? Number(farm.herdSize) : undefined,
      });
      setResult(data);
    } catch (err) {
      setResult(null);
      setError(getErrorMessage(err, "Compare failed."));
    } finally {
      setLoading(false);
    }
  };

  const deltas = result?.comparison?.deltas_a_minus_b || {};

  return (
    <div className="space-y-4">
      <div>
        <h1 className="font-display text-lg font-semibold text-veld-900">
          Compare camps
        </h1>
        <p className="mt-1 text-sm text-ink-muted">
          Compare pasture health, rainfall outlook, and grazing recommendations
          between two supported locations.
        </p>
      </div>

      <Card title="Locations">
        <form onSubmit={handleCompare} className="space-y-3 text-sm">
          <label className="block">
            <span className="text-xs font-semibold text-ink-muted">Location A</span>
            <select
              value={locationA}
              onChange={(e) => setLocationA(e.target.value)}
              className="mt-1 w-full rounded-xl border border-veld-200 px-3 py-2"
            >
              {NAMIBIA_LOCATIONS.map((loc) => (
                <option key={`a-${loc.name}`} value={loc.name}>
                  {loc.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-semibold text-ink-muted">Location B</span>
            <select
              value={locationB}
              onChange={(e) => setLocationB(e.target.value)}
              className="mt-1 w-full rounded-xl border border-veld-200 px-3 py-2"
            >
              {NAMIBIA_LOCATIONS.map((loc) => (
                <option key={`b-${loc.name}`} value={loc.name}>
                  {loc.name}
                </option>
              ))}
            </select>
          </label>
          <button
            type="submit"
            disabled={loading || locationA === locationB}
            className="w-full rounded-xl bg-veld-800 py-3 font-semibold text-white disabled:opacity-60"
          >
            {loading ? "Comparing…" : "Compare"}
          </button>
        </form>
      </Card>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}
      {loading && <Loader label="Comparing locations…" />}

      {result?.found && (
        <div className="space-y-3">
          <Card title="Summary">
            <p className="text-sm leading-relaxed text-ink">
              {result.farmer_summary ||
                result.comparison?.farmer_summary ||
                "Comparison complete."}
            </p>
          </Card>

          <div>
            <p className="mb-2 text-xs font-semibold uppercase text-ink-muted">
              {locationA}
            </p>
            <ActionPriorityBanner decision={result.decision_a} />
          </div>
          <div>
            <p className="mb-2 text-xs font-semibold uppercase text-ink-muted">
              {locationB}
            </p>
            <ActionPriorityBanner decision={result.decision_b} />
          </div>

          <button
            type="button"
            onClick={() => setShowTech((v) => !v)}
            className="text-[11px] font-semibold text-veld-700"
          >
            {showTech ? "Hide technical deltas" : "View technical deltas"}
          </button>

          {showTech && (
            <Card title="Technical deltas (A − B)">
              <dl className="space-y-2 text-sm">
                {Object.entries(deltas).map(([key, value]) => (
                  <div key={key} className="flex justify-between gap-3">
                    <dt className="text-ink-muted">{key.replace(/_/g, " ")}</dt>
                    <dd className="font-semibold">{formatValue(value)}</dd>
                  </div>
                ))}
              </dl>
              <ul className="mt-3 space-y-1 text-xs text-ink-muted">
                {(result.comparison?.notes || []).map((n) => (
                  <li key={n}>• {n}</li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      )}

      {result && !result.found && (
        <Card title="Could not compare">
          <p className="text-sm text-ink-muted">
            {result.message || "One or both locations were not found."}
          </p>
        </Card>
      )}
    </div>
  );
}
