import { useState } from "react";
import Card from "../Card";
import { formatValue } from "../../utils/format";

export default function RainfallImpactCard({
  decision,
  weather,
  title = "Rainfall & Grass Recovery",
  guestMode = false,
}) {
  const [open, setOpen] = useState(false);
  const impact = decision?.rainfall_impact;
  if (!impact && !weather) return null;

  const outlook =
    impact?.outlook ||
    weather?.message ||
    "Rainfall outlook is not available for this location yet.";
  const bullets = impact?.impact_bullets || [];
  const details = impact?.details || {};
  const guestBullets = bullets.slice(0, 2);

  return (
    <Card title={title}>
      <div className="space-y-3 text-sm">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
            Current Outlook
          </p>
          <p className="mt-1 leading-relaxed text-ink">{outlook}</p>
        </div>

        {guestBullets.length > 0 && (
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
              Impact on Grazing
            </p>
            <ul className="mt-1.5 space-y-1.5">
              {guestBullets.map((item) => (
                <li key={item} className="flex gap-2 text-ink">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-veld-600" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            {guestMode && bullets.length > guestBullets.length ? (
              <p className="mt-2 text-xs text-ink-muted">
                Log in to see the full impact list and evidence.
              </p>
            ) : null}
          </div>
        )}

        {!guestMode && decision?.confidence && (
          <div className="rounded-xl bg-mist px-3 py-2.5">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
              Data Quality
            </p>
            <p className="mt-0.5 text-sm font-semibold capitalize text-veld-900">
              {decision.confidence.level}
            </p>
            <p className="mt-1 text-xs leading-relaxed text-ink-muted">
              {decision.confidence.explanation}
            </p>
          </div>
        )}

        {!guestMode && (
          <>
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              className="text-[11px] font-semibold text-veld-700"
            >
              {open ? "Hide Rainfall Details" : "View Rainfall Details"}
            </button>

            {open && (
              <dl className="space-y-2 border-t border-veld-100 pt-3">
                <Detail
                  label="Recent rain total"
                  value={
                    details.recent_mm != null
                      ? `${details.recent_mm} mm (last ${details.recent_days || "?"} days)`
                      : weather?.rainfall_last_7_days || weather?.rainfall_recent
                  }
                />
                <Detail
                  label="Forecast rain total"
                  value={
                    details.forecast_mm != null
                      ? `${details.forecast_mm} mm`
                      : weather?.forecast_total_mm != null
                        ? `${weather.forecast_total_mm} mm`
                        : null
                  }
                />
                <Detail
                  label="Near-term temperature"
                  value={details.temperature || weather?.temperature}
                />
                <Detail label="Near-term rain" value={weather?.rainfall} />
                <Detail label="Source" value={weather?.source || "open-meteo"} />
              </dl>
            )}
          </>
        )}
      </div>
    </Card>
  );
}

function Detail({ label, value }) {
  if (value == null || value === "") return null;
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-ink-muted">{label}</dt>
      <dd className="font-semibold text-veld-900">{formatValue(value)}</dd>
    </div>
  );
}
