export default function ErrorAlert({ message, onDismiss }) {
  if (!message) return null;

  return (
    <div
      className="flex items-start gap-3 rounded-xl border border-danger/20 bg-danger-bg px-4 py-3 text-sm text-danger"
      role="alert"
    >
      <svg
        className="mt-0.5 h-4 w-4 shrink-0"
        viewBox="0 0 20 20"
        fill="currentColor"
        aria-hidden="true"
      >
        <path
          fillRule="evenodd"
          d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z"
          clipRule="evenodd"
        />
      </svg>
      <p className="flex-1 leading-relaxed">{message}</p>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="shrink-0 rounded-md px-1.5 py-0.5 text-xs font-semibold uppercase tracking-wide hover:bg-danger/10"
        >
          Dismiss
        </button>
      )}
    </div>
  );
}
