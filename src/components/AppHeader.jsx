import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { useFarmContext } from "../context/FarmContext";

const SCREENS = {
  "/": {
    title: "Farmar",
    hint: (farm) => farm.location,
  },
  "/chat": {
    title: "Ask",
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
    title: "Weather",
    hint: (farm) => farm.location,
  },
  "/profile": {
    title: "Profile",
    hint: (farm) => farm.farmerName || "Your farm details",
  },
};

export default function AppHeader({ action }) {
  const { pathname } = useLocation();
  const farm = useFarmContext();
  const screen = SCREENS[pathname] || SCREENS["/"];
  const [visible, setVisible] = useState(true);
  const [display, setDisplay] = useState(screen);

  useEffect(() => {
    setVisible(false);
    const timer = window.setTimeout(() => {
      setDisplay(SCREENS[pathname] || SCREENS["/"]);
      setVisible(true);
    }, 120);
    return () => window.clearTimeout(timer);
  }, [pathname]);

  const hint = display.hint(farm);

  return (
    <header className="safe-top sticky top-0 z-30 border-b border-veld-100/80 bg-white/90 px-4 py-3 backdrop-blur-xl">
      <div className="flex items-center justify-between gap-3">
        <div
          className={`min-w-0 transition-all duration-200 ease-out ${
            visible
              ? "translate-y-0 opacity-100"
              : "translate-y-1 opacity-0"
          }`}
        >
          <h1 className="truncate font-display text-xl font-bold tracking-tight text-veld-900">
            {display.title}
          </h1>
          {hint && (
            <p className="mt-0.5 truncate text-xs font-medium text-ink-muted">
              {hint}
            </p>
          )}
        </div>
        {action}
      </div>
    </header>
  );
}
