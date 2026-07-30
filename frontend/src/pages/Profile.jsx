import { useEffect, useState } from "react";
import Card from "../components/Card";
import {
  LAND_TENURE_OPTIONS,
  LIVESTOCK_OPTIONS,
  NAMIBIA_LOCATIONS,
  WATER_SOURCE_OPTIONS,
} from "../utils/constants";
import { useFarmContext } from "../context/FarmContext";

const FORM_KEYS = [
  "farmerName",
  "farmName",
  "phone",
  "location",
  "village",
  "customLocation",
  "herdSize",
  "livestockType",
  "campName",
  "numberOfCamps",
  "farmSizeHa",
  "landTenure",
  "waterSource",
  "farmNotes",
];

function pickForm(farm) {
  return FORM_KEYS.reduce((acc, key) => {
    acc[key] = farm[key] ?? "";
    return acc;
  }, {});
}

export default function Profile() {
  const farm = useFarmContext();
  const [form, setForm] = useState(() => pickForm(farm));
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setForm(pickForm(farm));
  }, [
    farm.farmerName,
    farm.farmName,
    farm.phone,
    farm.location,
    farm.village,
    farm.customLocation,
    farm.herdSize,
    farm.livestockType,
    farm.campName,
    farm.numberOfCamps,
    farm.farmSizeHa,
    farm.landTenure,
    farm.waterSource,
    farm.farmNotes,
  ]);

  const setField = (key, value) => {
    setSaved(false);
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleLocationChange = (name) => {
    setSaved(false);
    setForm((prev) => ({
      ...prev,
      location: name,
    }));
  };

  const handleSave = (event) => {
    event.preventDefault();
    farm.setLocationByName(form.location);
    farm.update({
      farmerName: String(form.farmerName).trim(),
      farmName: String(form.farmName).trim(),
      phone: String(form.phone).trim(),
      village: String(form.village).trim(),
      customLocation: String(form.customLocation).trim(),
      herdSize:
        form.herdSize === "" ? "" : Number(form.herdSize) || form.herdSize,
      livestockType: form.livestockType,
      campName: String(form.campName).trim(),
      numberOfCamps:
        form.numberOfCamps === ""
          ? ""
          : Number(form.numberOfCamps) || form.numberOfCamps,
      farmSizeHa:
        form.farmSizeHa === ""
          ? ""
          : Number(form.farmSizeHa) || form.farmSizeHa,
      landTenure: form.landTenure,
      waterSource: form.waterSource,
      farmNotes: String(form.farmNotes).trim(),
    });
    setSaved(true);
  };

  const handleReset = () => {
    farm.reset();
    setSaved(false);
  };

  const initials = (form.farmerName || form.farmName || "F")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "F";

  const selectedRegion =
    NAMIBIA_LOCATIONS.find((loc) => loc.name === form.location)?.region ||
    farm.region;

  return (
    <div className="space-y-4 pb-2">
      <Card>
        <div className="flex items-center gap-3">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-veld-800 font-display text-xl font-bold text-white">
            {initials}
          </div>
          <div className="min-w-0">
            <p className="truncate font-display text-lg font-semibold text-veld-900">
              {form.farmerName || form.farmName || "Your profile"}
            </p>
            <p className="truncate text-sm text-ink-muted">
              {[form.customLocation || form.village || form.location, selectedRegion]
                .filter(Boolean)
                .join(" · ")}
              {form.herdSize ? ` · ${form.herdSize} head` : ""}
            </p>
          </div>
        </div>
      </Card>

      <form onSubmit={handleSave} className="space-y-4">
        <Card title="About you">
          <div className="space-y-3">
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
            <Field label="Farm / homestead name" htmlFor="profile-farm-name">
              <input
                id="profile-farm-name"
                type="text"
                value={form.farmName}
                onChange={(e) => setField("farmName", e.target.value)}
                placeholder="e.g. Green Valley Farm"
                className="field-input"
              />
            </Field>
            <Field label="Phone (optional)" htmlFor="profile-phone">
              <input
                id="profile-phone"
                type="tel"
                inputMode="tel"
                value={form.phone}
                onChange={(e) => setField("phone", e.target.value)}
                placeholder="e.g. 081 234 5678"
                className="field-input"
              />
            </Field>
          </div>
        </Card>

        <Card title="Location">
          <div className="space-y-3">
            <Field label="Nearest town" htmlFor="profile-location">
              <select
                id="profile-location"
                value={form.location}
                onChange={(e) => handleLocationChange(e.target.value)}
                className="field-input"
              >
                {NAMIBIA_LOCATIONS.map((loc) => (
                  <option key={loc.name} value={loc.name}>
                    {loc.name}
                    {loc.mapsTo && loc.mapsTo !== loc.name
                      ? ` → ${loc.mapsTo}`
                      : ""}{" "}
                    ({loc.region})
                  </option>
                ))}
              </select>
            </Field>
            <p className="text-xs text-ink-muted">Region: {selectedRegion}</p>

            <Field label="Village / settlement" htmlFor="profile-village">
              <input
                id="profile-village"
                type="text"
                value={form.village}
                onChange={(e) => setField("village", e.target.value)}
                placeholder="e.g. Okakarara"
                className="field-input"
              />
            </Field>

            <Field
              label="Area notes (not used for data lookup)"
              htmlFor="profile-custom-location"
            >
              <input
                id="profile-custom-location"
                type="text"
                value={form.customLocation}
                onChange={(e) => setField("customLocation", e.target.value)}
                placeholder="Optional notes, e.g. 20km east of town"
                className="field-input"
              />
              <p className="mt-1 text-[11px] text-ink-muted">
                Pasture data uses the town/site above. Free text here is notes only.
              </p>
            </Field>
          </div>
        </Card>

        <Card title="Herd & camps">
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
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
              <Field label="Livestock" htmlFor="profile-livestock">
                <select
                  id="profile-livestock"
                  value={form.livestockType}
                  onChange={(e) => setField("livestockType", e.target.value)}
                  className="field-input"
                >
                  {LIVESTOCK_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </Field>
            </div>

            <Field label="Main camp / paddock" htmlFor="profile-camp">
              <input
                id="profile-camp"
                type="text"
                value={form.campName}
                onChange={(e) => setField("campName", e.target.value)}
                placeholder="e.g. North camp"
                className="field-input"
              />
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Number of camps" htmlFor="profile-camps">
                <input
                  id="profile-camps"
                  type="number"
                  min="1"
                  inputMode="numeric"
                  value={form.numberOfCamps}
                  onChange={(e) => setField("numberOfCamps", e.target.value)}
                  placeholder="e.g. 4"
                  className="field-input"
                />
              </Field>
              <Field label="Farm size (ha)" htmlFor="profile-size">
                <input
                  id="profile-size"
                  type="number"
                  min="0"
                  step="any"
                  inputMode="decimal"
                  value={form.farmSizeHa}
                  onChange={(e) => setField("farmSizeHa", e.target.value)}
                  placeholder="e.g. 2500"
                  className="field-input"
                />
              </Field>
            </div>

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

            <Field label="Water source" htmlFor="profile-water">
              <select
                id="profile-water"
                value={form.waterSource}
                onChange={(e) => setField("waterSource", e.target.value)}
                className="field-input"
              >
                {WATER_SOURCE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Notes about your farm" htmlFor="profile-notes">
              <textarea
                id="profile-notes"
                rows={3}
                value={form.farmNotes}
                onChange={(e) => setField("farmNotes", e.target.value)}
                placeholder="e.g. Bush encroachment on south camp, borehole low this season…"
                className="field-input resize-none"
              />
            </Field>
          </div>
        </Card>

        <button
          type="submit"
          className="flex w-full items-center justify-center rounded-xl bg-veld-800 py-3.5 text-sm font-semibold text-white active:bg-veld-900"
        >
          {saved ? "Saved" : "Save changes"}
        </button>
      </form>

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
