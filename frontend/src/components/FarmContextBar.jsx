import { NAMIBIA_LOCATIONS } from "../utils/constants";
import { useFarmContext } from "../context/FarmContext";

export default function FarmContextBar() {
  const farm = useFarmContext();

  return (
    <div className="grid grid-cols-[1fr_5.5rem] gap-2 border-b border-veld-100 bg-white px-3 py-2.5">
      <select
        aria-label="Location"
        value={farm.location}
        onChange={(e) => farm.setLocationByName(e.target.value)}
        className="w-full rounded-xl border border-veld-200 bg-mist px-3 py-2.5 text-sm font-medium outline-none focus:border-veld-500"
      >
        {NAMIBIA_LOCATIONS.map((loc) => (
          <option key={loc.name} value={loc.name}>
            {loc.name}
          </option>
        ))}
      </select>
      <input
        aria-label="Herd size"
        type="number"
        min="1"
        inputMode="numeric"
        value={farm.herdSize}
        onChange={(e) => farm.update({ herdSize: e.target.value })}
        placeholder="Herd"
        className="w-full rounded-xl border border-veld-200 bg-mist px-2 py-2.5 text-center text-sm font-medium outline-none focus:border-veld-500"
      />
    </div>
  );
}
