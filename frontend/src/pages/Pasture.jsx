import { useEffect, useState } from "react";
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

function preferDetailsOpen() {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(max-width: 1023px)").matches;
}

export default function Pasture() {
  const farm = useFarmContext();
  const { isLoggedIn } = useAuth();
  const { data, isLoading, error, fetchPasture, setError } = usePasture();
  const { data: dash, refetch: refetchDash } = useDashboard();
  const [detailsOpen, setDetailsOpen] = useState(preferDetailsOpen);

  const load = (location) => {
    if (!location) {
      setError("Select a supported town or research site.");
      return;
    }
    fetchPasture(location, { region: farm.region });
  };

  const openDetails = () => {
    setDetailsOpen(true);
    load(datasetLocation(farm));
    refetchDash();
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    openDetails();
  };

  useEffect(() => {
    const location = datasetLocation(farm);
    if (location && !data && !isLoading) {
      load(location);
    }
    // Phone: keep scrollable details handy. Laptop: map-first until Check.
    setDetailsOpen(preferDetailsOpen());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [farm.location]);

  const decision = dash?.decision;
  const pasture = data || dash?.pasture_status;
  const limitations = toArray(pasture?.limitations);
  const hasResults = Boolean(decision || pasture);

  const onSelectSite = (siteName) => {
    const match = NAMIBIA_LOCATIONS.find(
      (loc) =>
        loc.name === siteName ||
        loc.mapsTo === siteName ||
        loc.name.toLowerCase() === String(siteName).toLowerCase()
    );
    if (match) {
      farm.setLocationByName(match.name);
      fetchPasture(match.name, { region: match.region || farm.region });
    } else {
      farm.update({ location: siteName });
      fetchPasture(siteName, { region: farm.region });
    }
    refetchDash();
    setDetailsOpen(true);
  };

  return (
    <div className="mx-auto w-full max-w-5xl space-y-4 lg:space-y-5">
      {!isLoggedIn ? (
        <GuestBanner detail="Guests can check pasture health. Log in for full technical details and limitations." />
      ) : null}

      <div className="mx-auto w-full">
        <SiteMap
          selectedLocation={farm.location}
          onSelectSite={onSelectSite}
          decision={detailsOpen ? decision : null}
        />
      </div>

      <form
        onSubmit={handleSubmit}
        className="mx-auto flex w-full max-w-xl flex-col gap-2 sm:flex-row sm:items-center"
      >
        <select
          aria-label="Location"
          value={farm.location}
          onChange={(e) => {
            farm.setLocationByName(e.target.value);
            if (!preferDetailsOpen()) setDetailsOpen(false);
          }}
          className="min-w-0 flex-1 rounded-xl border border-veld-200 bg-white px-3.5 py-3 text-sm font-medium outline-none focus:border-veld-500"
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
          className="rounded-xl bg-veld-800 px-5 py-3 text-sm font-semibold text-white active:bg-veld-900 disabled:opacity-60 sm:shrink-0"
        >
          {isLoading ? "Loading…" : "Check pasture"}
        </button>
      </form>

      {error && (
        <div className="mx-auto w-full max-w-xl">
          <ErrorAlert message={error} onDismiss={() => setError(null)} />
        </div>
      )}

      <div className="mx-auto w-full max-w-3xl">
        {!detailsOpen ? (
          <button
            type="button"
            onClick={openDetails}
            className="flex w-full items-center justify-between gap-3 rounded-2xl border border-dashed border-veld-200 bg-white/80 px-4 py-3.5 text-left transition hover:border-veld-400 hover:bg-white"
          >
            <div>
              <p className="text-sm font-semibold text-veld-900">
                Pasture details
              </p>
              <p className="mt-0.5 text-xs text-ink-muted">
                Click Check pasture to see health and advice for{" "}
                {farm.location || "this camp"}.
              </p>
            </div>
            <span className="shrink-0 text-lg leading-none text-veld-600" aria-hidden>
              ▾
            </span>
          </button>
        ) : (
          <div className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-veld-100">
            <button
              type="button"
              onClick={() => setDetailsOpen(false)}
              className="flex w-full items-center justify-between gap-3 border-b border-veld-100 px-4 py-3 text-left hover:bg-mist/60"
            >
              <div>
                <p className="text-sm font-semibold text-veld-900">
                  Pasture details · {farm.location}
                </p>
                <p className="mt-0.5 text-xs text-ink-muted">
                  Hide to focus on the map again
                </p>
              </div>
              <span className="shrink-0 text-lg leading-none text-veld-600" aria-hidden>
                ▴
              </span>
            </button>

            <div className="space-y-3 p-4">
              {isLoading && <Loader label="Loading pasture…" />}

              {!isLoading && hasResults && (
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

              {!isLoading && !hasResults && (
                <p className="text-sm text-ink-muted">
                  No pasture reading for this location yet. Try another camp on
                  the map.
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
