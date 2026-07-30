import { useState } from "react";
import Card from "../components/Card";
import ErrorAlert from "../components/ErrorAlert";
import Loader from "../components/Loader";
import ActionPriorityBanner from "../components/decision/ActionPriorityBanner";
import { useFarmContext } from "../context/FarmContext";
import { runScenario } from "../services/api";
import { NAMIBIA_LOCATIONS, datasetLocation } from "../utils/constants";
import { getErrorMessage } from "../utils/format";

export default function Scenarios() {
  const farm = useFarmContext();
  const [scenarioHerd, setScenarioHerd] = useState(farm.herdSize || 50);
  const [assumeRain, setAssumeRain] = useState("");
  const [moveDays, setMoveDays] = useState("");
  const [altLocation, setAltLocation] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleRun = async (event) => {
    event.preventDefault();
    const location = datasetLocation(farm);
    if (!location) {
      setError("Select a supported town or research site in your profile.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await runScenario({
        location,
        land_tenure: farm.landTenure,
        current_herd_size: farm.herdSize ? Number(farm.herdSize) : null,
        scenario_herd_size: scenarioHerd === "" ? null : Number(scenarioHerd),
        assume_rain_mm: assumeRain === "" ? null : Number(assumeRain),
        move_in_days: moveDays === "" ? null : Number(moveDays),
        alternate_location: altLocation || null,
        livestock_type: farm.livestockType || "cattle",
      });
      setResult(data);
    } catch (err) {
      setResult(null);
      setError(getErrorMessage(err, "Scenario failed."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="font-display text-lg font-semibold text-veld-900">
          Scenario Planner
        </h1>
        <p className="mt-1 text-sm text-ink-muted">
          Explore what-if decisions before you act. This is planning support —
          not a prediction engine, and it never invents vegetation growth.
        </p>
      </div>

      <Card title="What if…">
        <form onSubmit={handleRun} className="space-y-3 text-sm">
          <p className="text-xs text-ink-muted">
            Current location: <strong>{farm.location}</strong>
            {farm.herdSize ? ` · herd ${farm.herdSize}` : ""}
          </p>
          <label className="block">
            <span className="text-xs font-semibold text-ink-muted">Scenario herd size</span>
            <input
              type="number"
              min="1"
              value={scenarioHerd}
              onChange={(e) => setScenarioHerd(e.target.value)}
              className="mt-1 w-full rounded-xl border border-veld-200 px-3 py-2"
            />
          </label>
          <label className="block">
            <span className="text-xs font-semibold text-ink-muted">
              Assume rainfall this week (mm, optional)
            </span>
            <input
              type="number"
              min="0"
              step="0.1"
              value={assumeRain}
              onChange={(e) => setAssumeRain(e.target.value)}
              placeholder="e.g. 15"
              className="mt-1 w-full rounded-xl border border-veld-200 px-3 py-2"
            />
          </label>
          <label className="block">
            <span className="text-xs font-semibold text-ink-muted">
              Move planning window (days, optional)
            </span>
            <input
              type="number"
              min="1"
              value={moveDays}
              onChange={(e) => setMoveDays(e.target.value)}
              placeholder="e.g. 7"
              className="mt-1 w-full rounded-xl border border-veld-200 px-3 py-2"
            />
          </label>
          <label className="block">
            <span className="text-xs font-semibold text-ink-muted">
              Alternate camp / site (optional)
            </span>
            <select
              value={altLocation}
              onChange={(e) => setAltLocation(e.target.value)}
              className="mt-1 w-full rounded-xl border border-veld-200 px-3 py-2"
            >
              <option value="">Same location</option>
              {NAMIBIA_LOCATIONS.map((loc) => (
                <option key={loc.name} value={loc.name}>
                  {loc.name}
                </option>
              ))}
            </select>
          </label>
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-veld-800 py-3 font-semibold text-white disabled:opacity-60"
          >
            {loading ? "Comparing…" : "Compare scenario"}
          </button>
        </form>
      </Card>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}
      {loading && <Loader label="Running scenario…" />}

      {result && (
        <div className="space-y-3">
          <p className="text-xs text-ink-muted">{result.disclaimer}</p>
          <Card title="What changed">
            <ul className="space-y-2 text-sm">
              {(result.what_changed || []).map((item) => (
                <li key={item} className="flex gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-veld-600" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </Card>
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">
              Current
            </p>
            <ActionPriorityBanner decision={result.current} />
          </div>
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">
              Scenario
            </p>
            <ActionPriorityBanner decision={result.scenario} />
          </div>
          {(result.scenario?.scenario_notes || []).length > 0 && (
            <Card title="Scenario notes">
              <ul className="space-y-2 text-sm text-ink-muted">
                {result.scenario.scenario_notes.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
