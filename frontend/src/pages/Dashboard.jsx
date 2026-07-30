import { Link } from "react-router-dom";
import Card from "../components/Card";
import ErrorAlert from "../components/ErrorAlert";
import GuestBanner from "../components/GuestBanner";
import Loader from "../components/Loader";
import ActionPriorityBanner from "../components/decision/ActionPriorityBanner";
import GrazingConditionsCard from "../components/decision/GrazingConditionsCard";
import RainfallImpactCard from "../components/decision/RainfallImpactCard";
import PastureHealthCard from "../components/decision/PastureHealthCard";
import DecisionTimeline from "../components/decision/DecisionTimeline";
import RecommendationExplainer from "../components/decision/RecommendationExplainer";
import { useDashboard } from "../hooks/useDashboard";
import { useFarmContext } from "../context/FarmContext";
import { useAuth } from "../context/AuthContext";
import { formatValue, toArray } from "../utils/format";
import { NAMIBIA_LOCATIONS } from "../utils/constants";

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
  const { isLoggedIn } = useAuth();
  const { data, isLoading, error, refetch, isFetching } = useDashboard();
  const decision = data?.decision;

  return (
    <div className="mx-auto w-full max-w-6xl space-y-4 lg:space-y-5">
      {!isLoggedIn ? <GuestBanner /> : null}

      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="flex min-w-0 flex-1 items-center gap-2 lg:max-w-md">
          <select
            aria-label="Location"
            value={farm.location}
            onChange={(e) => farm.setLocationByName(e.target.value)}
            className="min-w-0 flex-1 rounded-xl border border-veld-200 bg-white px-3 py-2.5 text-sm font-medium outline-none focus:border-veld-500"
          >
            {NAMIBIA_LOCATIONS.map((loc) => (
              <option key={loc.name} value={loc.name}>
                {loc.name}
                {loc.mapsTo && loc.mapsTo !== loc.name ? ` → ${loc.mapsTo}` : ""}
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

        <div className="flex flex-col gap-2 sm:flex-row lg:shrink-0">
          <Link
            to="/chat"
            className="flex flex-1 items-center justify-center rounded-xl bg-veld-800 py-3 text-sm font-semibold text-white active:bg-veld-900 sm:flex-none sm:px-6"
          >
            Ask advisor
          </Link>
          <Link
            to="/compare"
            className="flex flex-1 items-center justify-center rounded-xl border border-veld-200 bg-white py-2.5 text-sm font-semibold text-veld-800 sm:flex-none sm:px-5"
          >
            Compare camps
          </Link>
        </div>
      </div>
      <p className="text-[11px] text-ink-muted lg:text-xs">
        Ask anything — including what-ifs about herd size, rain, or moving camps.
      </p>

      {error && <ErrorAlert message={error} />}

      {isLoading ? (
        <Loader label="Loading grazing advice…" />
      ) : data ? (
        <div className="space-y-3 lg:space-y-4">
          {decision && <ActionPriorityBanner decision={decision} />}
          <div className="grid gap-3 lg:grid-cols-2 lg:gap-4">
            {decision && <GrazingConditionsCard decision={decision} />}
            {isLoggedIn && decision && <DecisionTimeline decision={decision} />}
            {decision ? (
              <PastureHealthCard decision={decision} pasture={data.pasture_status} />
            ) : (
              <Card title="Pasture">
                <p className="text-sm text-ink-muted">
                  {data.pasture_status?.message || "No pasture decision yet."}
                </p>
              </Card>
            )}
            {decision ? (
              <RainfallImpactCard decision={decision} weather={data.weather} />
            ) : (
              <Card title="Rainfall & Grass Recovery">
                <p className="text-sm text-ink-muted">
                  {data.weather?.message || "No rainfall outlook yet."}
                </p>
              </Card>
            )}
          </div>
          {isLoggedIn && decision && (
            <RecommendationExplainer
              decision={decision}
              sources={{
                pasture: data.pasture_status,
                weather: data.weather,
                grazing_assessment: data.grazing_assessment,
              }}
            />
          )}
          <div className="grid gap-3 lg:grid-cols-2 lg:gap-4">
            {isLoggedIn && toArray(data.alerts).length > 0 && (
              <Card title="Alerts">
                <SimpleList items={data.alerts} empty="" />
              </Card>
            )}
            {isLoggedIn && toArray(data.recommendations).length > 0 && (
              <Card title="Tips">
                <SimpleList items={data.recommendations} empty="" />
              </Card>
            )}
          </div>
          {!isLoggedIn ? (
            <p className="text-center text-xs text-ink-muted">
              Log in to see the full timeline, evidence panel, alerts, and tips.
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
