import Card from "../components/Card";
import ErrorAlert from "../components/ErrorAlert";
import Loader from "../components/Loader";
import { useDashboard } from "../hooks/useDashboard";
import { formatLabel, formatValue, toArray } from "../utils/format";

function MetricList({ data }) {
  if (!data || (typeof data === "object" && Object.keys(data).length === 0)) {
    return <p className="text-sm text-ink-muted">No data available.</p>;
  }

  if (typeof data !== "object") {
    return <p className="text-2xl font-semibold text-veld-900">{formatValue(data)}</p>;
  }

  return (
    <dl className="space-y-3">
      {Object.entries(data).map(([key, value]) => (
        <div
          key={key}
          className="flex items-start justify-between gap-4 border-b border-veld-100 pb-2 last:border-0 last:pb-0"
        >
          <dt className="text-sm text-ink-muted">{formatLabel(key)}</dt>
          <dd className="text-right text-sm font-semibold text-veld-900">
            {formatValue(value)}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function ListBlock({ items, emptyLabel }) {
  const list = toArray(items);
  if (list.length === 0) {
    return <p className="text-sm text-ink-muted">{emptyLabel}</p>;
  }

  return (
    <ul className="space-y-2.5">
      {list.map((item, index) => (
        <li
          key={index}
          className="flex gap-2.5 rounded-xl bg-veld-50 px-3 py-2.5 text-sm text-ink"
        >
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-sun-500" />
          <span>
            {typeof item === "string" ? item : JSON.stringify(item)}
          </span>
        </li>
      ))}
    </ul>
  );
}

export default function Dashboard() {
  const { data, isLoading, error, refetch, isFetching } = useDashboard();

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sun-600">
            Overview
          </p>
          <h1 className="mt-1 font-display text-3xl font-bold tracking-tight text-veld-900 sm:text-4xl">
            Farmar Dashboard
          </h1>
          <p className="mt-2 max-w-xl text-sm text-ink-muted sm:text-base">
            Weather, pasture condition, alerts, and recommendations for your
            rangeland — at a glance.
          </p>
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          className="inline-flex items-center justify-center rounded-xl border border-veld-200 bg-white px-4 py-2.5 text-sm font-semibold text-veld-800 transition hover:bg-veld-50 disabled:opacity-60"
        >
          {isFetching ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {error && <ErrorAlert message={error} />}

      {isLoading ? (
        <Loader label="Loading dashboard…" />
      ) : data ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <Card
            title="Weather"
            subtitle="Current conditions"
            icon={
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364 1.386l-1.591 1.591M21 12h-2.25m-1.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" />
              </svg>
            }
          >
            <MetricList data={data.weather} />
          </Card>

          <Card
            title="Pasture Status"
            subtitle="Field condition"
            icon={
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 3c2.5 4 6 9 8 14H4c2-5 5.5-10 8-14z" />
              </svg>
            }
          >
            <MetricList data={data.pasture_status} />
          </Card>

          <Card
            title="Alerts"
            subtitle="Needs attention"
            icon={
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
              </svg>
            }
          >
            <ListBlock items={data.alerts} emptyLabel="No active alerts." />
          </Card>

          <Card
            title="Recommendations"
            subtitle="Suggested actions"
            icon={
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
          >
            <ListBlock
              items={data.recommendations}
              emptyLabel="No recommendations yet."
            />
          </Card>
        </div>
      ) : (
        !error && (
          <Card>
            <p className="text-sm text-ink-muted">
              No dashboard data returned from the API.
            </p>
          </Card>
        )
      )}
    </div>
  );
}
