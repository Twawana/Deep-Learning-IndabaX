/** Shared styles for action priority / health levels */

export const PRIORITY_STYLES = {
  stay: {
    badge: "bg-emerald-100 text-emerald-900 ring-emerald-200",
    bar: "bg-emerald-700",
    dot: "bg-emerald-500",
    emoji: "🟢",
  },
  monitor: {
    badge: "bg-amber-100 text-amber-950 ring-amber-200",
    bar: "bg-amber-600",
    dot: "bg-amber-500",
    emoji: "🟡",
  },
  move_soon: {
    badge: "bg-orange-100 text-orange-950 ring-orange-200",
    bar: "bg-orange-600",
    dot: "bg-orange-500",
    emoji: "🟠",
  },
  move_now: {
    badge: "bg-red-100 text-red-950 ring-red-200",
    bar: "bg-red-700",
    dot: "bg-red-500",
    emoji: "🔴",
  },
};

export const HEALTH_STYLES = {
  good: PRIORITY_STYLES.stay,
  fair: PRIORITY_STYLES.monitor,
  stressed: PRIORITY_STYLES.move_soon,
  poor: PRIORITY_STYLES.move_now,
  unknown: {
    badge: "bg-stone-100 text-stone-800 ring-stone-200",
    bar: "bg-stone-500",
    dot: "bg-stone-400",
    emoji: "⚪",
  },
};

export function priorityStyle(key) {
  return PRIORITY_STYLES[key] || PRIORITY_STYLES.monitor;
}

export function healthStyle(key) {
  return HEALTH_STYLES[key] || HEALTH_STYLES.unknown;
}
