import Card from "../Card";
import { priorityStyle } from "./priorityStyles";
import StatusDot from "./StatusDot";

export default function GrazingConditionsCard({ decision }) {
  const gc = decision?.grazing_conditions;
  if (!gc) return null;
  const style = priorityStyle(gc.action_priority || decision.action_priority);

  return (
    <Card title="Grazing Conditions">
      <div className="space-y-3 text-sm">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
            Overall Status
          </p>
          <p className={`mt-1 inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${style.badge}`}>
            <StatusDot style={style} />
            {gc.overall_status}
          </p>
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
            Pasture
          </p>
          <p className="mt-1 leading-relaxed text-ink">{gc.pasture_summary}</p>
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
            Rainfall
          </p>
          <p className="mt-1 leading-relaxed text-ink">{gc.rainfall_summary}</p>
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
            Combined Assessment
          </p>
          <p className="mt-1 leading-relaxed text-ink">{gc.combined_assessment}</p>
        </div>
        <div className={`rounded-xl p-3 ring-1 ${style.badge}`}>
          <p className="text-[11px] font-semibold uppercase tracking-wide opacity-80">
            Recommended Action
          </p>
          <p className="mt-1 font-medium leading-relaxed">{gc.recommended_action}</p>
        </div>
        {decision.confidence && (
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
              Data Quality
            </p>
            <p className="mt-1 font-semibold text-veld-900 capitalize">
              {decision.confidence.level}
            </p>
            <p className="mt-1 text-xs leading-relaxed text-ink-muted">
              {decision.confidence.explanation}
            </p>
          </div>
        )}
      </div>
    </Card>
  );
}
