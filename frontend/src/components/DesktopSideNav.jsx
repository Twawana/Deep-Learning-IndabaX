import { Link, NavLink, useLocation } from "react-router-dom";
import { NAV_TABS } from "./navTabs";
import { useAuth } from "../context/AuthContext";

export default function DesktopSideNav() {
  const { pathname } = useLocation();
  const { isLoggedIn, isAdmin } = useAuth();

  return (
    <aside className="desktop-side-nav hidden shrink-0 flex-col border-r border-veld-100 bg-white/95 lg:flex">
      <div className="px-5 pb-4 pt-6">
        <Link to="/" className="block">
          <p className="font-display text-2xl font-bold tracking-tight text-veld-900">
            Farmar
          </p>
          <p className="mt-1 text-xs font-medium text-ink-muted">
            Rangeland advisor
          </p>
        </Link>
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3 pb-4" aria-label="Primary">
        {NAV_TABS.map((tab) => {
          const active = tab.match(pathname);
          const Icon = tab.icon;
          return (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.end}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition-colors ${
                active
                  ? "bg-veld-800 text-white"
                  : "text-ink-muted hover:bg-mist hover:text-veld-900"
              }`}
            >
              <Icon active={active} />
              {tab.label}
            </NavLink>
          );
        })}

        <div className="my-3 border-t border-veld-100" />

        <NavLink
          to="/compare"
          className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition-colors ${
            pathname.startsWith("/compare")
              ? "bg-veld-800 text-white"
              : "text-ink-muted hover:bg-mist hover:text-veld-900"
          }`}
        >
          <CompareIcon active={pathname.startsWith("/compare")} />
          Compare
        </NavLink>

        {isAdmin && (
          <NavLink
            to="/admin"
            className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition-colors ${
              pathname.startsWith("/admin")
                ? "bg-veld-800 text-white"
                : "text-ink-muted hover:bg-mist hover:text-veld-900"
            }`}
          >
            <AdminIcon active={pathname.startsWith("/admin")} />
            Admin
          </NavLink>
        )}
      </nav>

      <div className="border-t border-veld-100 px-4 py-4">
        {!isLoggedIn ? (
          <Link
            to="/profile"
            className="block rounded-xl bg-mist px-3 py-2.5 text-center text-sm font-semibold text-veld-800"
          >
            Log in
          </Link>
        ) : (
          <p className="text-center text-[11px] text-ink-muted">
            Namibian pasture guidance
          </p>
        )}
      </div>
    </aside>
  );
}

function CompareIcon({ active }) {
  return (
    <svg className="h-[1.15rem] w-[1.15rem]" fill={active ? "currentColor" : "none"} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={active ? 0 : 1.9}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 4.5v15m6-15v15M3.75 9h4.5m-4.5 6h4.5m6-6h4.5m-4.5 6h4.5" />
    </svg>
  );
}

function AdminIcon({ active }) {
  return (
    <svg className="h-[1.15rem] w-[1.15rem]" fill={active ? "currentColor" : "none"} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={active ? 0 : 1.9}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.174.1.347.223.52.337.27.178.637.15.89-.07l1.04-.9a1.125 1.125 0 011.45.12l1.792 1.95c.373.406.361 1.048-.027 1.44l-.95.97c-.22.226-.29.565-.19.87a8.4 8.4 0 010 .674c-.1.305-.03.644.19.87l.95.97c.388.392.4 1.034.027 1.44l-1.792 1.95c-.373.406-.998.48-1.45.12l-1.04-.9c-.253-.22-.62-.248-.89-.07a7.6 7.6 0 01-.52.337c-.332.184-.582.496-.645.87l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.063-.374-.313-.686-.645-.87a7.6 7.6 0 01-.52-.337c-.27-.178-.637-.15-.89.07l-1.04.9a1.125 1.125 0 01-1.45-.12l-1.792-1.95a1.125 1.125 0 01.027-1.44l.95-.97c.22-.226.29-.565.19-.87a8.4 8.4 0 010-.674c.1-.305.03-.644-.19-.87l-.95-.97a1.125 1.125 0 01-.027-1.44l1.792-1.95c.373-.406.998-.48 1.45-.12l1.04.9c.253.22.62.248.89.07.172-.114.345-.237.52-.337.332-.184.582-.496.645-.87l.213-1.28z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  );
}
