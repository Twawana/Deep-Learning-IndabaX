import { useState } from "react";
import Card from "../Card";
import { formatValue } from "../../utils/format";

export default function RecommendationExplainer({ decision, sources, toolsUsed }) {
  const [open, setOpen] = useState(false);
  const explainer = decision?.explainer;
  if (!explainer) return null;

  const checks = explainer.checks || [];
  const why = explainer.why || [];

  return (
    <Card title="Why this recommendation?">
      <div className="space-y-3 text-sm">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
            What should I do?
          </p>
          <p className="mt-1 leading-relaxed text-ink">{explainer.what}</p>
        </div>

        <ul className="space-y-1.5">
          {checks.map((check) => (
            <li key={check.id} className="flex gap-2 text-sm text-ink">
              <span className={check.done ? "text-emerald-700" : "text-ink-muted"}>
                {check.done ? "✓" : "○"}
              </span>
              <span>{check.label}</span>
            </li>
          ))}
        </ul>

        {why.length > 0 && (
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
              Why?
            </p>
            <ul className="mt-1.5 space-y-1.5">
              {why.map((item) => (
                <li key={item} className="flex gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-sun-500" />
                  <span className="leading-relaxed text-ink">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {explainer.what_if_not && (
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
              What happens if I don&apos;t?
            </p>
            <p className="mt-1 leading-relaxed text-ink">{explainer.what_if_not}</p>
          </div>
        )}

        {(explainer.monitor_next || []).length > 0 && (
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
              What should I monitor next?
            </p>
            <ul className="mt-1.5 space-y-1.5">
              {explainer.monitor_next.map((item) => (
                <li key={item} className="flex gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-veld-600" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="text-[11px] font-semibold text-veld-700"
        >
          {open ? "Hide Evidence" : "View Evidence"}
        </button>

        {open && (
          <div className="space-y-2 border-t border-veld-100 pt-3 text-xs text-ink-muted">
            {(toolsUsed || []).length > 0 && (
              <p>
                Tools used:{" "}
                {(toolsUsed || [])
                  .map((t) => (typeof t === "string" ? t : t?.name || String(t)))
                  .join(", ")}
              </p>
            )}
            {sources?.pasture && (
              <p>
                Pasture: cover {formatValue(sources.pasture.vegetation_cover)}
                {sources.pasture.vegetation_cover != null ? "%" : ""}, biomass{" "}
                {formatValue(sources.pasture.biomass)}, bush{" "}
                {formatValue(sources.pasture.bush_encroachment)}
                {sources.pasture.bush_encroachment != null ? "%" : ""}
              </p>
            )}
            {sources?.weather && (
              <p>
                Rainfall: recent {formatValue(sources.weather.recent_rainfall_mm)} mm,
                forecast {formatValue(sources.weather.forecast_total_mm)} mm
              </p>
            )}
            {sources?.grazing_assessment && (
              <p>
                Grazing risk: {formatValue(sources.grazing_assessment.grazing_risk)} (
                {formatValue(sources.grazing_assessment.confidence)} confidence)
              </p>
            )}
            {decision?.confidence && (
              <p>{decision.confidence.explanation}</p>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}
