import { useEffect } from "react";
import ErrorAlert from "../components/ErrorAlert";
import GuestBanner from "../components/GuestBanner";
import Loader from "../components/Loader";
import RainfallImpactCard from "../components/decision/RainfallImpactCard";
import { useFarmContext } from "../context/FarmContext";
import { useAuth } from "../context/AuthContext";
import { useWeather } from "../hooks/useWeather";
import { useDashboard } from "../hooks/useDashboard";
import { NAMIBIA_LOCATIONS, datasetLocation } from "../utils/constants";

export default function Weather() {
  const farm = useFarmContext();
  const { isLoggedIn } = useAuth();
  const { data, isLoading, error, fetchWeather, setError } = useWeather();
  const { data: dash } = useDashboard();

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

  // Auto-load once for current farm location
  useEffect(() => {
    const location = datasetLocation(farm);
    if (location && !data && !isLoading) {
      fetchWeather(farm.lat, farm.lon, { days: 7, location, region: farm.region });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [farm.location]);

  const decision = dash?.decision;
  const weather = data || dash?.weather;

  return (
    <div className="mx-auto w-full max-w-3xl space-y-4 lg:max-w-4xl">
      {!isLoggedIn ? (
        <GuestBanner detail="Guests see the rainfall outlook. Log in for full impact details and data quality notes." />
      ) : null}
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
          {isLoading ? "Loading…" : "Check rainfall impact"}
        </button>
      </form>

      {error && (
        <ErrorAlert message={error} onDismiss={() => setError(null)} />
      )}

      {isLoading && <Loader label="Loading rainfall outlook…" />}

      {!isLoading && weather && (
        <RainfallImpactCard
          decision={decision}
          weather={weather}
          title="Rainfall & Grass Recovery"
          guestMode={!isLoggedIn}
        />
      )}
    </div>
  );
}
