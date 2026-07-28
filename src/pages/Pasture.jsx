import { useState } from "react";
import Card from "../components/Card";
import ErrorAlert from "../components/ErrorAlert";
import Loader from "../components/Loader";
import { usePasture } from "../hooks/usePasture";
import { NAMIBIA_LOCATIONS } from "../utils/constants";
import { formatValue } from "../utils/format";

export default function Pasture() {
  const [location, setLocation] = useState("Windhoek");
  const [customLocation, setCustomLocation] = useState("");
  const { data, isLoading, error, fetchPasture, setError } = usePasture();

  const handleSubmit = (event) => {
    event.preventDefault();
    const query = customLocation.trim() || location;
    fetchPasture(query);
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sun-600">
          Field data
        </p>
        <h1 className="mt-1 font-display text-3xl font-bold tracking-tight text-veld-900 sm:text-4xl">
          Pasture Conditions
        </h1>
        <p className="mt-2 max-w-xl text-sm text-ink-muted sm:text-base">
          Check soil quality, grass type, and overall pasture condition for a
          selected location.
        </p>
      </div>

      <Card title="Location" subtitle="Select a town or enter a custom area">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="pasture-location"
                className="mb-1.5 block text-sm font-medium text-ink"
              >
                Region / town
              </label>
              <select
                id="pasture-location"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full rounded-xl border border-veld-200 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-veld-500 focus:ring-2 focus:ring-veld-200"
              >
                {NAMIBIA_LOCATIONS.map((loc) => (
                  <option key={loc.name} value={loc.name}>
                    {loc.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label
                htmlFor="pasture-custom"
                className="mb-1.5 block text-sm font-medium text-ink"
              >
                Custom location (optional)
              </label>
              <input
                id="pasture-custom"
                type="text"
                value={customLocation}
                onChange={(e) => setCustomLocation(e.target.value)}
                placeholder="e.g. Otjozondjupa camp 3"
                className="w-full rounded-xl border border-veld-200 bg-white px-3.5 py-2.5 text-sm outline-none placeholder:text-ink-muted/70 focus:border-veld-500 focus:ring-2 focus:ring-veld-200"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className="inline-flex items-center justify-center rounded-xl bg-veld-800 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-veld-900 disabled:opacity-60"
          >
            {isLoading ? "Fetching…" : "Fetch pasture data"}
          </button>
        </form>
      </Card>

      {error && (
        <ErrorAlert message={error} onDismiss={() => setError(null)} />
      )}

      {isLoading && <Loader label="Loading pasture data…" />}

      {!isLoading && data && (
        <div className="grid gap-4 sm:grid-cols-3">
          <Card title="Soil Quality">
            <p className="font-display text-2xl font-semibold text-veld-900">
              {formatValue(data.soil_quality)}
            </p>
          </Card>
          <Card title="Grass Type">
            <p className="font-display text-2xl font-semibold text-veld-900">
              {formatValue(data.grass_type)}
            </p>
          </Card>
          <Card title="Condition">
            <p className="font-display text-2xl font-semibold text-veld-900">
              {formatValue(data.condition)}
            </p>
          </Card>
        </div>
      )}
    </div>
  );
}
