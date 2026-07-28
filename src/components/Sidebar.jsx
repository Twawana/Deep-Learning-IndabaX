import { NavLink } from "react-router-dom";

const links = [
  {
    to: "/",
    label: "Dashboard",
    end: true,
    description: "Overview & alerts",
  },
  {
    to: "/chat",
    label: "AI Advisor",
    description: "Ask grazing questions",
  },
  {
    to: "/pasture",
    label: "Pasture",
    description: "Soil & grass condition",
  },
  {
    to: "/weather",
    label: "Weather",
    description: "Rainfall & climate",
  },
];

export default function Sidebar() {
  return (
    <aside className="hidden w-56 shrink-0 lg:block">
      <div className="sticky top-20 rounded-2xl border border-veld-200/80 bg-white/70 p-3 shadow-sm backdrop-blur-sm">
        <p className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-ink-muted">
          Navigate
        </p>
        <nav className="space-y-1">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                `block rounded-xl px-3 py-2.5 transition ${
                  isActive
                    ? "bg-veld-800 text-white"
                    : "text-ink hover:bg-veld-50"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <span className="block text-sm font-semibold">{link.label}</span>
                  <span
                    className={`mt-0.5 block text-xs ${
                      isActive ? "text-veld-200" : "text-ink-muted"
                    }`}
                  >
                    {link.description}
                  </span>
                </>
              )}
            </NavLink>
          ))}
        </nav>
      </div>
    </aside>
  );
}
