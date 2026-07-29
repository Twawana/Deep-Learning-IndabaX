import { useEffect, useState } from "react";
import Card from "../components/Card";
import {
  LAND_TENURE_OPTIONS,
  NAMIBIA_LOCATIONS,
} from "../utils/constants";
import { useFarmContext } from "../context/FarmContext";

export default function Profile() {
  const farm = useFarmContext();
  const [form, setForm] = useState({
    farmerName: farm.farmerName,
    location: farm.location,
    herdSize: farm.herdSize,
    campName: farm.campName,
    landTenure: farm.landTenure,
  });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setForm({
      farmerName: farm.farmerName,
      location: farm.location,
      herdSize: farm.herdSize,
      campName: farm.campName,
      landTenure: farm.landTenure,
    });
  }, [farm.farmerName, farm.location, farm.herdSize, farm.campName, farm.landTenure]);

  const setField = (key, value) => {
    setSaved(false);
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = (event) => {
    event.preventDefault();
    farm.setLocationByName(form.location);
    farm.update({
      farmerName: form.farmerName.trim(),
      herdSize: form.herdSize === "" ? "" : Number(form.herdSize) || form.herdSize,
      campName: form.campName.trim(),
      landTenure: form.landTenure,
    });
    setSaved(true);
  };

  const handleReset = () => {
    farm.reset();
    setSaved(false);
  };

  const initials = (form.farmerName || "F")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "F";

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex items-center gap-3">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-veld-800 font-display text-xl font-bold text-white">
            {initials}
          </div>
          <div className="min-w-0">
            <p className="truncate font-display text-lg font-semibold text-veld-900">
              {form.farmerName || "Your profile"}
            </p>
            <p className="truncate text-sm text-ink-muted">
              {form.location}
              {form.herdSize ? ` · ${form.herdSize} head` : ""}
            </p>
          </div>
        </div>
      </Card>

      <Card title="Farm details">
        <form onSubmit={handleSave} className="space-y-3">
          <Field label="Your name" htmlFor="profile-name">
            <input
              id="profile-name"
              type="text"
              value={form.farmerName}
              onChange={(e) => setField("farmerName", e.target.value)}
              placeholder="e.g. Maria"
              className="field-input"
            />
          </Field>

          <Field label="Location" htmlFor="profile-location">
            <select
              id="profile-location"
              value={form.location}
              onChange={(e) => setField("location", e.target.value)}
              className="field-input"
            >
              {NAMIBIA_LOCATIONS.map((loc) => (
                <option key={loc.name} value={loc.name}>
                  {loc.name}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Herd size" htmlFor="profile-herd">
            <input
              id="profile-herd"
              type="number"
              min="1"
              inputMode="numeric"
              value={form.herdSize}
              onChange={(e) => setField("herdSize", e.target.value)}
              className="field-input"
            />
          </Field>

          <Field label="Camp / paddock" htmlFor="profile-camp">
            <input
              id="profile-camp"
              type="text"
              value={form.campName}
              onChange={(e) => setField("campName", e.target.value)}
              placeholder="e.g. North camp"
              className="field-input"
            />
          </Field>

          <Field label="Land type" htmlFor="profile-tenure">
            <select
              id="profile-tenure"
              value={form.landTenure}
              onChange={(e) => setField("landTenure", e.target.value)}
              className="field-input"
            >
              {LAND_TENURE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </Field>

          <button
            type="submit"
            className="flex w-full items-center justify-center rounded-xl bg-veld-800 py-3.5 text-sm font-semibold text-white active:bg-veld-900"
          >
            {saved ? "Saved" : "Save changes"}
          </button>
        </form>
      </Card>

      <button
        type="button"
        onClick={handleReset}
        className="w-full py-2 text-sm font-semibold text-ink-muted"
      >
        Reset to defaults
      </button>
    </div>
  );
}

function Field({ label, htmlFor, children }) {
  return (
    <div>
      <label
        htmlFor={htmlFor}
        className="mb-1.5 block text-sm font-medium text-ink"
      >
        {label}
      </label>
      {children}
    </div>
  );
}
