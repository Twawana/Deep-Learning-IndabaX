export default function Card({ title, children, className = "", action }) {
  return (
    <section
      className={`rounded-2xl bg-white p-4 shadow-sm ring-1 ring-veld-100 ${className}`}
    >
      {(title || action) && (
        <header className="mb-3 flex items-center justify-between gap-2">
          {title && (
            <h2 className="font-display text-base font-semibold text-veld-900">
              {title}
            </h2>
          )}
          {action}
        </header>
      )}
      {children}
    </section>
  );
}
