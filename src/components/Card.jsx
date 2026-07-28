export default function Card({
  title,
  subtitle,
  icon,
  children,
  className = "",
  action,
}) {
  return (
    <section
      className={`rounded-2xl border border-veld-200/80 bg-white/80 p-5 shadow-sm backdrop-blur-sm ${className}`}
    >
      {(title || icon || action) && (
        <header className="mb-4 flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            {icon && (
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-veld-100 text-veld-800">
                {icon}
              </div>
            )}
            <div>
              {title && (
                <h2 className="font-display text-lg font-semibold text-veld-900">
                  {title}
                </h2>
              )}
              {subtitle && (
                <p className="mt-0.5 text-sm text-ink-muted">{subtitle}</p>
              )}
            </div>
          </div>
          {action}
        </header>
      )}
      <div>{children}</div>
    </section>
  );
}
