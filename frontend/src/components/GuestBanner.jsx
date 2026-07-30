import { Link } from "react-router-dom";

export default function GuestBanner({
  title = "Browsing as guest",
  detail = "You can check basic pasture and weather now. Log in to unlock full details, unlimited Oryx, and Premium AI.",
}) {
  return (
    <div className="rounded-xl border border-veld-200 bg-white px-3 py-2.5">
      <p className="text-sm font-semibold text-veld-900">{title}</p>
      <p className="mt-0.5 text-xs text-ink-muted">{detail}</p>
      <Link
        to="/profile"
        className="mt-2 inline-block text-xs font-semibold text-veld-700"
      >
        Log in on Profile →
      </Link>
    </div>
  );
}
