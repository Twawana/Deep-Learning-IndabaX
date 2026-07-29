export default function Loader({ label = "Loading…", compact = false }) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-2 ${
        compact ? "py-2" : "py-8"
      }`}
      role="status"
    >
      <div
        className={`animate-spin rounded-full border-[3px] border-veld-200 border-t-veld-700 ${
          compact ? "h-5 w-5" : "h-8 w-8"
        }`}
        aria-hidden="true"
      />
      {label && (
        <p className={`font-medium text-ink-muted ${compact ? "text-xs" : "text-sm"}`}>
          {label}
        </p>
      )}
    </div>
  );
}
