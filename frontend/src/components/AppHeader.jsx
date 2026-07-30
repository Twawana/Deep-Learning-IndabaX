import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useFarmContext } from "../context/FarmContext";
import { useAuth } from "../context/AuthContext";

const SCREENS = {
  "/": {
    title: "Farmar",
    hint: (farm) => farm.location,
  },
  "/chat": {
    title: "Ask In Vision",
    hint: (farm) =>
      farm.herdSize
        ? `${farm.location} · ${farm.herdSize} head`
        : farm.location,
  },
  "/pasture": {
    title: "Pasture",
    hint: (farm) => farm.location,
  },
  "/weather": {
    title: "Rainfall",
    hint: (farm) => farm.location,
  },
  "/compare": {
    title: "Compare camps",
    hint: () => "Side-by-side grazing advice",
  },
  "/profile": {
    title: "Profile",
    hint: (farm) =>
      farm.farmName || farm.farmerName || farm.customLocation || "Your farm details",
  },
  "/admin": {
    title: "Admin",
    hint: () => "Manage users and app controls",
  },
};

function resolveScreen(pathname) {
  if (SCREENS[pathname]) return SCREENS[pathname];
  if (pathname.startsWith("/compare")) return SCREENS["/compare"];
  if (pathname.startsWith("/admin")) return SCREENS["/admin"];
  return SCREENS["/"];
}

export default function AppHeader({ action }) {
  const { pathname } = useLocation();
  const farm = useFarmContext();
  const { isLoggedIn, isPremium, currentUser } = useAuth();
  const screen = resolveScreen(pathname);
  const [visible, setVisible] = useState(true);
  const [display, setDisplay] = useState(screen);

  useEffect(() => {
    setVisible(false);
    const timer = window.setTimeout(() => {
      setDisplay(resolveScreen(pathname));
      setVisible(true);
    }, 120);
    return () => window.clearTimeout(timer);
  }, [pathname]);

  const hint = display.hint(farm);

  return (
    <header className="safe-top sticky top-0 z-[1100] border-b border-veld-100/80 bg-white/90 px-4 py-3 backdrop-blur-xl lg:px-8 lg:py-4">
      <div className="flex items-center justify-between gap-3">
        <div
          className={`min-w-0 transition-all duration-200 ease-out ${
            visible
              ? "translate-y-0 opacity-100"
              : "translate-y-1 opacity-0"
          }`}
        >
          <h1 className="truncate font-display text-xl font-bold tracking-tight text-veld-900 lg:text-2xl">
            {display.title}
          </h1>
          {hint && (
            <p className="mt-0.5 truncate text-xs font-medium text-ink-muted lg:text-sm">
              {hint}
            </p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {!isLoggedIn ? (
            <Link
              to="/profile"
              className="rounded-full bg-mist px-2.5 py-1 text-[11px] font-semibold text-veld-800 ring-1 ring-veld-100 lg:px-3.5 lg:py-1.5 lg:text-xs"
            >
              Log in
            </Link>
          ) : (
            <Link
              to="/profile"
              className="max-w-[7rem] truncate rounded-full bg-veld-800 px-2.5 py-1 text-[11px] font-semibold text-white lg:max-w-[12rem] lg:px-3.5 lg:py-1.5 lg:text-xs"
              title={currentUser?.name}
            >
              {isPremium ? "Premium" : currentUser?.name?.split(" ")[0] || "Account"}
            </Link>
          )}
          {action}
        </div>
      </div>
    </header>
  );
}
