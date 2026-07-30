import { useEffect } from "react";
import Card from "../components/Card";
import ErrorAlert from "../components/ErrorAlert";
import GuestBanner from "../components/GuestBanner";
import Loader from "../components/Loader";
import ActionPriorityBanner from "../components/decision/ActionPriorityBanner";
import PastureHealthCard from "../components/decision/PastureHealthCard";
import SiteMap from "../components/decision/SiteMap";
import { useFarmContext } from "../context/FarmContext";
import { useAuth } from "../context/AuthContext";
import { usePasture } from "../hooks/usePasture";
import { useDashboard } from "../hooks/useDashboard";
import { NAMIBIA_LOCATIONS, datasetLocation } from "../utils/constants";
import { toArray } from "../utils/format";

export default function Pasture() {
  const farm = useFarmContext();
  const { isLoggedIn } = useAuth();
  const { data, isLoading, error, fetchPasture, setError } = usePasture();
  const { data: dash, refetch: refetchDash } = useDashboard();

  const load = (location) => {
    if (!location) {
      setError("Select a supported town or research site.");
      return;
    }
    fetchPasture(location, { region: farm.region });
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    load(datasetLocation(farm));
  };

  useEffect(() => {
    const location = datasetLocation(farm);
    if (location && !data && !isLoading) {
      load(location);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [farm.location]);

  const decision = dash?.decision;
  const pasture = data || dash?.pasture_status;
  const limitations = toArray(pasture?.limitations);

  const onSelectSite = (siteName) => {
    const match = NAMIBIA_LOCATIONS.find(
      (loc) =>
        loc.name === siteName ||
        loc.mapsTo === siteName ||
        loc.name.toLowerCase() === String(siteName).toLowerCase()
    );
    if (match) {
      farm.setLocationByName(match.name);
      load(match.name);
    } else {
      farm.update({ location: siteName });
      load(siteName);
    }
    refetchDash();
  };

  return (
    <div className="space-y-4">
      {!isLoggedIn ? (
        <GuestBanner detail="Guests can check pasture health. Log in for full technical details and limitations." />
      ) : null}

      <SiteMap
        selectedLocation={farm.location}
        onSelectSite={onSelectSite}
        decision={decision}
      />

      <form onSubmit={handleSubmit} className="space-y-3">
        <select
          aria-label="Location"
          value={farm.location}
          onChange={(e) => {
            farm.setLocationByName(e.target.value);
          }}
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
          {isLoading ? "Loading…" : "Check pasture health"}
        </button>
      </form>

      {error && (
        <ErrorAlert message={error} onDismiss={() => setError(null)} />
      )}

      {isLoading && <Loader label="Loading pasture…" />}

      {!isLoading && (decision || pasture) && (
        <>
          {decision && <ActionPriorityBanner decision={decision} />}
          <PastureHealthCard decision={decision} pasture={pasture} />
          {isLoggedIn && limitations.length > 0 && (
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
