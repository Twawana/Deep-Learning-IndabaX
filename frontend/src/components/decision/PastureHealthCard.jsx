import { useState } from "react";
import Card from "../Card";
import { formatValue } from "../../utils/format";
import { healthStyle } from "./priorityStyles";
import StatusDot from "./StatusDot";

export default function PastureHealthCard({ decision, pasture }) {
  const [open, setOpen] = useState(false);
  const health = decision?.pasture_health;
  if (!health && !pasture) return null;

  const level = health?.level || "unknown";
  const style = healthStyle(level);
  const summary =
    health?.summary ||
    pasture?.message ||
    "Pasture summary is not available for this location yet.";
  const technical = health?.technical || [];

  return (
    <Card title="Pasture Health">
      <div className="space-y-3 text-sm">
        <p className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${style.badge}`}>
          <StatusDot style={style} />
          {health?.label || "Uncertain"}
        </p>
        <p className="leading-relaxed text-ink">{summary}</p>
        {health?.observation_date && (
          <p className="text-xs text-ink-muted">
            Latest field observation date: {health.observation_date}
            {health.sites?.length ? ` · Sites: ${health.sites.join(", ")}` : ""}
          </p>
        )}

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="text-[11px] font-semibold text-veld-700"
        >
          {open ? "Hide Technical Details" : "View Technical Details"}
        </button>

        {open && (
          <div className="space-y-3 border-t border-veld-100 pt-3">
            {technical.map((item) => (
              <div key={item.key}>
                <div className="flex justify-between gap-3">
                  <p className="font-semibold text-veld-900">{item.label}</p>
                  <p className="font-semibold text-veld-900">
                    {item.value == null || item.value === ""
                      ? "Unavailable"
                      : `${formatValue(item.value)}${item.unit ? item.unit : ""}`}
                  </p>
                </div>
                <p className="mt-0.5 text-[11px] text-ink-muted">
                  {item.technical_name}: {item.plain_language}
                </p>
              </div>
            ))}
            {!technical.length && pasture?.found && (
              <dl className="space-y-2">
                {[
                  ["vegetation_cover", "Vegetation Health"],
                  ["biomass", "Available Grazing"],
                  ["bush_encroachment", "Bush / Woody Cover"],
                  ["grazing_pressure", "Current Grazing Pressure"],
                ].map(([key, label]) =>
                  pasture[key] != null ? (
                    <div key={key} className="flex justify-between gap-3">
                      <dt className="text-ink-muted">{label}</dt>
                      <dd className="font-semibold">{formatValue(pasture[key])}</dd>
                    </div>
                  ) : null
                )}
              </dl>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}
