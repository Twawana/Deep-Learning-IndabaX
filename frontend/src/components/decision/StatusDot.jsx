/** Small status marker — replaces emoji circles in decision UI */

export default function StatusDot({ style, className = "" }) {
  return (
    <span
      aria-hidden="true"
      className={`inline-block h-2 w-2 shrink-0 rounded-full ${style?.dot || "bg-stone-400"} ${className}`}
    />
  );
}
