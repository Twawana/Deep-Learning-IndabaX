import { useState } from "react";
import Card from "../components/Card";
import ErrorAlert from "../components/ErrorAlert";
import Loader from "../components/Loader";
import { useWeather } from "../hooks/useWeather";
import { NAMIBIA_LOCATIONS } from "../utils/constants";
import { formatValue } from "../utils/format";

export default function Weather() {
  const [lat, setLat] = useState("-22.57");
  const [lon, setLon] = useState("17.08");
  const [selectedLocation, setSelectedLocation] = useState("Windhoek");
  const { data, isLoading, error, fetchWeather, setError } = useWeather();

  const handleLocationChange = (name) => {
    setSelectedLocation(name);
    const match = NAMIBIA_LOCATIONS.find((loc) => loc.name === name);
    if (match) {
      setLat(String(match.lat));
      setLon(String(match.lon));
    }
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    fetchWeather(lat, lon);
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sun-600">
          Climate
        </p>
        <h1 className="mt-1 font-display text-3xl font-bold tracking-tight text-veld-900 sm:text-4xl">
          Weather Data
        </h1>
        <p className="mt-2 max-w-xl text-sm text-ink-muted sm:text-base">
          Look up temperature, rainfall, and humidity by coordinates or a known
          Namibian location.
        </p>
      </div>

      <Card title="Coordinates" subtitle="Pick a location or enter lat / lon">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="weather-location"
              className="mb-1.5 block text-sm font-medium text-ink"
            >
              Quick location
            </label>
            <select
              id="weather-location"
              value={selectedLocation}
              onChange={(e) => handleLocationChange(e.target.value)}
              className="w-full rounded-xl border border-veld-200 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-veld-500 focus:ring-2 focus:ring-veld-200 sm:max-w-xs"
            >
              {NAMIBIA_LOCATIONS.map((loc) => (
                <option key={loc.name} value={loc.name}>
                  {loc.name}
                </option>
              ))}
            </select>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="weather-lat"
                className="mb-1.5 block text-sm font-medium text-ink"
              >
                Latitude
              </label>
              <input
                id="weather-lat"
                type="number"
                step="any"
                value={lat}
                onChange={(e) => setLat(e.target.value)}
                className="w-full rounded-xl border border-veld-200 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-veld-500 focus:ring-2 focus:ring-veld-200"
                required
              />
            </div>
            <div>
              <label
                htmlFor="weather-lon"
                className="mb-1.5 block text-sm font-medium text-ink"
              >
                Longitude
              </label>
              <input
                id="weather-lon"
                type="number"
                step="any"
                value={lon}
                onChange={(e) => setLon(e.target.value)}
                className="w-full rounded-xl border border-veld-200 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-veld-500 focus:ring-2 focus:ring-veld-200"
                required
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="inline-flex items-center justify-center rounded-xl bg-veld-800 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-veld-900 disabled:opacity-60"
          >
            {isLoading ? "Fetching…" : "Fetch weather"}
          </button>
        </form>
      </Card>

      {error && (
        <ErrorAlert message={error} onDismiss={() => setError(null)} />
      )}

      {isLoading && <Loader label="Loading weather data…" />}

      {!isLoading && data && (
        <div className="grid gap-4 sm:grid-cols-3">
          <Card title="Temperature">
            <p className="font-display text-2xl font-semibold text-veld-900">
              {formatValue(data.temperature)}
            </p>
          </Card>
          <Card title="Rainfall">
            <p className="font-display text-2xl font-semibold text-veld-900">
              {formatValue(data.rainfall)}
            </p>
          </Card>
          <Card title="Humidity">
            <p className="font-display text-2xl font-semibold text-veld-900">
              {formatValue(data.humidity)}
            </p>
          </Card>
        </div>
      )}
    </div>
  );
}
