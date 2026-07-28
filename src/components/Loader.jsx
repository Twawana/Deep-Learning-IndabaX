export default function Loader({ label = "Loading…" }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-10" role="status">
      <div
        className="h-9 w-9 animate-spin rounded-full border-[3px] border-veld-200 border-t-veld-700"
        aria-hidden="true"
      />
      <p className="text-sm font-medium text-ink-muted">{label}</p>
    </div>
  );
}
