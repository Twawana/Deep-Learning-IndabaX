import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";

const tabs = [
  {
    to: "/",
    label: "Home",
    end: true,
    match: (path) => path === "/",
    icon: HomeIcon,
  },
  {
    to: "/chat",
    label: "Ask",
    match: (path) => path.startsWith("/chat"),
    icon: AskIcon,
  },
  {
    to: "/pasture",
    label: "Pasture",
    match: (path) => path.startsWith("/pasture"),
    icon: PastureIcon,
  },
  {
    to: "/weather",
    label: "Rainfall",
    match: (path) => path.startsWith("/weather"),
    icon: WeatherIcon,
  },
  {
    to: "/profile",
    label: "Profile",
    match: (path) => path.startsWith("/profile"),
    icon: ProfileIcon,
  },
];

function HomeIcon({ active }) {
  return (
    <svg className="h-[1.15rem] w-[1.15rem]" fill={active ? "currentColor" : "none"} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={active ? 0 : 1.9}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12l8.954-8.955a1.126 1.126 0 011.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
    </svg>
  );
}

function AskIcon({ active }) {
  return (
    <svg className="h-[1.15rem] w-[1.15rem]" fill={active ? "currentColor" : "none"} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={active ? 0 : 1.9}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.75 20.25c.818 0 1.607-.13 2.345-.372A9 9 0 0121 12z" />
    </svg>
  );
}

function PastureIcon({ active }) {
  return (
    <svg className="h-[1.15rem] w-[1.15rem]" fill={active ? "currentColor" : "none"} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={active ? 0 : 1.9}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3c2.5 4 6 9 8 14H4c2-5 5.5-10 8-14z" />
      <path strokeLinecap="round" d="M12 8v9" />
    </svg>
  );
}

function WeatherIcon({ active }) {
  return (
    <svg className="h-[1.15rem] w-[1.15rem]" fill={active ? "currentColor" : "none"} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={active ? 0 : 1.9}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364 1.386l-1.591 1.591M21 12h-2.25m-1.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" />
    </svg>
  );
}

function ProfileIcon({ active }) {
  return (
    <svg className="h-[1.15rem] w-[1.15rem]" fill={active ? "currentColor" : "none"} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={active ? 0 : 1.9}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
    </svg>
  );
}

export default function BottomTabBar() {
  const { pathname } = useLocation();
  const navRef = useRef(null);
  const itemRefs = useRef([]);
  const [indicator, setIndicator] = useState({ left: 0, width: 0, ready: false });
  const [pressed, setPressed] = useState(null);

  const matchedIndex = tabs.findIndex((tab) => tab.match(pathname));
  const activeIndex = matchedIndex >= 0 ? matchedIndex : -1;

  const updateIndicator = () => {
    if (activeIndex < 0) {
      setIndicator((prev) => ({ ...prev, ready: false }));
      return;
    }
    const el = itemRefs.current[activeIndex];
    const track = navRef.current;
    if (!el || !track) return;
    setIndicator({
      left: el.offsetLeft,
      width: el.offsetWidth,
      ready: true,
    });
  };

  useLayoutEffect(() => {
    updateIndicator();
  }, [activeIndex, pathname]);

  useEffect(() => {
    const onResize = () => updateIndicator();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [activeIndex]);

  return (
    <div className="floating-tab-shell pointer-events-none absolute inset-x-0 bottom-0 z-40 flex justify-center px-4">
      <nav
        className="floating-tab-bar pointer-events-auto"
        aria-label="Primary"
      >
        <div
          ref={navRef}
          className="relative grid h-[3.85rem] grid-cols-5 gap-0.5 px-1.5"
        >
          <span
            aria-hidden="true"
            className="nav-indicator pointer-events-none absolute top-1.5 bottom-1.5 rounded-[1.15rem] bg-veld-800/95 shadow-[0_8px_20px_rgba(26,58,42,0.28)]"
            style={{
              width: indicator.width,
              transform: `translateX(${indicator.left}px)`,
              opacity: indicator.ready ? 1 : 0,
            }}
          />

          {tabs.map((tab, index) => {
            const active = index === activeIndex;
            const Icon = tab.icon;

            return (
              <NavLink
                key={tab.to}
                to={tab.to}
                end={tab.end}
                ref={(node) => {
                  itemRefs.current[index] = node;
                }}
                onPointerDown={() => setPressed(index)}
                onPointerUp={() => setPressed(null)}
                onPointerLeave={() => setPressed(null)}
                onPointerCancel={() => setPressed(null)}
                className={`relative z-10 flex flex-col items-center justify-center gap-0.5 rounded-[1.15rem] text-[9px] font-semibold tracking-wide transition-transform duration-200 ${
                  active ? "text-white" : "text-ink-muted"
                } ${pressed === index ? "scale-90" : "scale-100"}`}
              >
                <span
                  className={`flex items-center justify-center transition-transform duration-300 ${
                    active ? "-translate-y-px scale-110" : ""
                  }`}
                >
                  <Icon active={active} />
                </span>
                <span
                  className={`leading-none transition-opacity duration-300 ${
                    active ? "opacity-100" : "opacity-65"
                  }`}
                >
                  {tab.label}
                </span>
              </NavLink>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
