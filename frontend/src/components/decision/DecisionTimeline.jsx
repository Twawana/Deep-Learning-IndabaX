import Card from "../Card";
import { priorityStyle } from "./priorityStyles";
import StatusDot from "./StatusDot";

const WHEN_LABELS = {
  today: "Today",
  "3_days": "3 Days",
  "7_days": "7 Days",
  "10_14_days": "10–14 Days",
};

export default function DecisionTimeline({ decision }) {
  const steps = decision?.timeline || [];
  if (!steps.length) return null;

  return (
    <Card title="Grazing Decision Timeline">
      <p className="mb-3 text-xs text-ink-muted">
        Planning aid based on current evidence — not a guaranteed prediction.
        Wording uses “based on current conditions” and “if rainfall remains low”.
      </p>
      <ol className="space-y-3">
        {steps.map((step) => {
          const style = priorityStyle(step.status || "monitor");
          return (
            <li key={step.when} className="flex gap-3">
              <StatusDot style={style} className="mt-1.5 h-2.5 w-2.5" />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
                    {WHEN_LABELS[step.when] || step.when}
                  </p>
                  <p
                    className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ${style.badge}`}
                  >
                    <StatusDot style={style} />
                    {step.label}
                  </p>
                </div>
                <p className="mt-1 text-sm leading-relaxed text-ink">{step.note}</p>
              </div>
            </li>
          );
        })}
      </ol>
    </Card>
  );
}
