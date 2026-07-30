import { priorityStyle } from "./priorityStyles";
import StatusDot from "./StatusDot";

export default function ActionPriorityBanner({ decision }) {
  if (!decision) return null;
  const priority = decision.action_priority || "monitor";
  const style = priorityStyle(priority);

  return (
    <section className={`rounded-2xl p-4 shadow-sm ring-1 ${style.badge}`}>
      <p className="text-[11px] font-semibold uppercase tracking-wide opacity-80">
        Current Grazing Recommendation
      </p>
      <h2 className="mt-1 flex items-center gap-2 font-display text-xl font-semibold">
        <StatusDot style={style} className="h-2.5 w-2.5" />
        {decision.headline || decision.overall_status_label}
      </h2>
      <p className="mt-2 text-sm leading-relaxed">
        {decision.recommended_action}
      </p>
    </section>
  );
}
