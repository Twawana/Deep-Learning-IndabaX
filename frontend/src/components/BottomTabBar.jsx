import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { NAV_TABS } from "./navTabs";

export default function BottomTabBar() {
  const { pathname } = useLocation();
  const navRef = useRef(null);
  const itemRefs = useRef([]);
  const [indicator, setIndicator] = useState({ left: 0, width: 0, ready: false });
  const [pressed, setPressed] = useState(null);

  const matchedIndex = NAV_TABS.findIndex((tab) => tab.match(pathname));
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
    <div className="floating-tab-shell pointer-events-none absolute inset-x-0 bottom-0 z-[1200] flex justify-center px-4 lg:hidden">
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

          {NAV_TABS.map((tab, index) => {
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
