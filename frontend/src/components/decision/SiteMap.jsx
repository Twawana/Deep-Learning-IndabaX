import { useEffect, useMemo, useState } from "react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { getRegions } from "../../services/api";
import { NAMIBIA_LOCATIONS } from "../../utils/constants";
import Card from "../Card";

/**
 * Colour like a farmer reading the veld from above:
 * greener = more living cover / healthier; browner/redder = thinner grass.
 * Prefer NDVI (satellite greenness), then vegetation cover %.
 */
function healthFromSite(site) {
  const ndvi = site?.ndvi;
  const cover = site?.vegetation_cover;
  const biomass = site?.biomass;
  const bush = site?.bush_encroachment;

  let score = null; // 0 = poor, 1 = healthy
  let basis = "unknown";

  if (ndvi != null && Number.isFinite(Number(ndvi))) {
    const n = Number(ndvi);
    // Typical dryland NDVI roughly 0.1–0.65 in this dataset
    score = Math.max(0, Math.min(1, (n - 0.12) / 0.45));
    basis = "ndvi";
  } else if (cover != null && Number.isFinite(Number(cover))) {
    score = Math.max(0, Math.min(1, Number(cover) / 50));
    basis = "cover";
  } else if (biomass != null && Number.isFinite(Number(biomass))) {
    const b = Number(biomass);
    // Lacuna field biomass is often <200; synthetic grass kg/ha is often 200+
    score = b >= 200 ? Math.max(0, Math.min(1, (b - 300) / 1200)) : Math.max(0, Math.min(1, b / 150));
    basis = "biomass";
  }

  // Heavy bush makes the camp look woodier / less open grass
  if (score != null && bush != null && bush >= 35) {
    score = Math.max(0, score - 0.12);
  }

  if (score == null) {
    return {
      color: "#a8a29e",
      label: "Unknown",
      hint: "No cover or greenness reading for this point.",
      score: null,
      basis,
    };
  }

  if (score >= 0.72) {
    return {
      color: "#16a34a",
      label: "Looks grassy",
      hint: "Stronger greenness / cover — more living plant signal.",
      score,
      basis,
    };
  }
  if (score >= 0.5) {
    return {
      color: "#65a30d",
      label: "Fair cover",
      hint: "Some grass signal, but not lush.",
      score,
      basis,
    };
  }
  if (score >= 0.32) {
    return {
      color: "#ca8a04",
      label: "Patchy",
      hint: "Thinner cover — grass looks patchy from above.",
      score,
      basis,
    };
  }
  if (score >= 0.18) {
    return {
      color: "#ea580c",
      label: "Thin grass",
      hint: "Low cover / greenness — camp looks bare or dry.",
      score,
      basis,
    };
  }
  return {
    color: "#b91c1c",
    label: "Very thin",
    hint: "Very low grass signal — treat as stressed veld.",
    score,
    basis,
  };
}

function markerRadius(site, isSelected) {
  const cover = site?.vegetation_cover;
  const base =
    cover == null
      ? 7
      : cover >= 40
        ? 11
        : cover >= 25
          ? 9
          : cover >= 15
            ? 7
            : 5;
  return isSelected ? base + 3 : base;
}

function haversineKm(a, b) {
  const toRad = (d) => (d * Math.PI) / 180;
  const R = 6371;
  const dLat = toRad(b.latitude - a.latitude);
  const dLon = toRad(b.longitude - a.longitude);
  const lat1 = toRad(a.latitude);
  const lat2 = toRad(b.latitude);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

function FocusSites({ sites, selected }) {
  const map = useMap();
  useEffect(() => {
    const pts = sites.filter((s) => s.latitude != null && s.longitude != null);
    if (!pts.length) {
      map.setView([-22.5, 17.5], 5);
      return;
    }
    if (selected?.latitude != null && selected?.longitude != null) {
      const nearby = pts.filter((s) => haversineKm(selected, s) <= 120);
      const focus = nearby.length >= 2 ? nearby : [selected];
      const lats = focus.map((s) => s.latitude);
      const lons = focus.map((s) => s.longitude);
      map.fitBounds(
        [
          [Math.min(...lats) - 0.25, Math.min(...lons) - 0.25],
          [Math.max(...lats) + 0.25, Math.max(...lons) + 0.25],
        ],
        { padding: [28, 28], maxZoom: 9 }
      );
      return;
    }
    const lats = pts.map((s) => s.latitude);
    const lons = pts.map((s) => s.longitude);
    map.fitBounds(
      [
        [Math.min(...lats) - 0.4, Math.min(...lons) - 0.4],
        [Math.max(...lats) + 0.4, Math.max(...lons) + 0.4],
      ],
      { padding: [24, 24] }
    );
  }, [map, sites, selected]);
  return null;
}

function LegendSwatch({ color, label }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className="inline-block h-2.5 w-2.5 rounded-full ring-1 ring-white/80"
        style={{ backgroundColor: color }}
        aria-hidden
      />
      {label}
    </span>
  );
}

export default function SiteMap({ selectedLocation, onSelectSite, decision }) {
  const [sites, setSites] = useState([]);
  const [error, setError] = useState(null);
  const [showNationwide, setShowNationwide] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getRegions()
      .then((data) => {
        if (cancelled) return;
        const apiSites = (data.sites || []).filter(
          (s) => s.latitude != null && s.longitude != null
        );
        if (apiSites.length) {
          setSites(apiSites);
          return;
        }
        setSites(
          NAMIBIA_LOCATIONS.map((loc) => ({
            site: loc.mapsTo || loc.name,
            region: loc.region,
            latitude: loc.lat,
            longitude: loc.lon,
            vegetation_cover: null,
            biomass: null,
            ndvi: null,
          }))
        );
      })
      .catch(() => {
        if (cancelled) return;
        setError("Map sites could not be loaded; using known town coordinates.");
        setSites(
          NAMIBIA_LOCATIONS.map((loc) => ({
            site: loc.mapsTo || loc.name,
            region: loc.region,
            latitude: loc.lat,
            longitude: loc.lon,
          }))
        );
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selected = useMemo(() => {
    const name = (selectedLocation || "").toLowerCase().trim();
    if (!name) return null;
    return (
      sites.find((s) => String(s.site).toLowerCase() === name) ||
      sites.find((s) => String(s.site).toLowerCase().includes(name)) ||
      sites.find((s) => String(s.region || "").toLowerCase() === name) ||
      null
    );
  }, [sites, selectedLocation]);

  /**
   * Keep the map readable: Lacuna field sites always, plus synthetic neighbours
   * around the selected camp so you can compare grass signal nearby.
   */
  const visibleSites = useMemo(() => {
    const withCoords = sites.filter(
      (s) => s.latitude != null && s.longitude != null
    );
    if (showNationwide) {
      // Cap dense synthetic cloud so the map stays usable
      const lacuna = withCoords.filter((s) => s.dataset_source !== "synthetic_v2");
      const synth = withCoords.filter((s) => s.dataset_source === "synthetic_v2");
      const step = Math.max(1, Math.ceil(synth.length / 180));
      return [...lacuna, ...synth.filter((_, i) => i % step === 0)];
    }
    if (!selected) {
      return withCoords.filter((s) => s.dataset_source !== "synthetic_v2");
    }
    const lacuna = withCoords.filter((s) => s.dataset_source !== "synthetic_v2");
    const nearbySynth = withCoords.filter(
      (s) =>
        s.dataset_source === "synthetic_v2" && haversineKm(selected, s) <= 120
    );
    const selectedIn = withCoords.filter(
      (s) => String(s.site) === String(selected.site)
    );
    const merged = new Map();
    [...lacuna, ...nearbySynth, ...selectedIn].forEach((s) => {
      merged.set(`${s.site}-${s.latitude}-${s.longitude}`, s);
    });
    return [...merged.values()];
  }, [sites, selected, showNationwide]);

  const selectedHealth = selected ? healthFromSite(selected) : null;

  return (
    <Card title="Grazing map">
      <p className="mb-2 text-xs leading-relaxed text-ink-muted">
        Read the dots like the veld from above:{" "}
        <span className="font-semibold text-veld-800">greener = more grass signal</span>
        , browner/redder = thinner cover. Marker size also follows cover (bigger =
        more cover). Tap a site to set your location.
        {selectedHealth?.label
          ? ` Your area: ${selectedHealth.label.toLowerCase()}.`
          : ""}
        {decision?.headline ? ` Advice: ${decision.headline}.` : ""}
      </p>
      {error && <p className="mb-2 text-xs text-amber-800">{error}</p>}

      <div className="mb-2 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setShowNationwide((v) => !v)}
          className="rounded-full bg-mist px-2.5 py-1 text-[11px] font-semibold text-veld-800 ring-1 ring-veld-100"
        >
          {showNationwide ? "Focus near my camp" : "Show wider Namibia sample"}
        </button>
        {selected && (
          <span className="text-[11px] text-ink-muted">
            Showing field sites
            {showNationwide ? " + sample nationwide" : " + synthetic neighbours (~120 km)"}
          </span>
        )}
      </div>

      <div className="grazing-map-shell h-72 rounded-xl ring-1 ring-veld-100 lg:h-[min(70vh,36rem)]">
        <MapContainer
          center={[-22.5, 17.5]}
          zoom={5}
          className="h-full w-full"
          scrollWheelZoom={false}
        >
          <TileLayer
            attribution="Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics"
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          />
          <FocusSites sites={visibleSites} selected={selected} />
          {visibleSites.map((site) => {
            const health = healthFromSite(site);
            const isSelected =
              selected && String(selected.site) === String(site.site);
            const dimmed =
              selected &&
              !isSelected &&
              haversineKm(selected, site) > 80;
            return (
              <CircleMarker
                key={`${site.site}-${site.latitude}-${site.longitude}`}
                center={[site.latitude, site.longitude]}
                radius={markerRadius(site, isSelected)}
                pathOptions={{
                  color: isSelected ? "#fff" : "rgba(255,255,255,0.85)",
                  weight: isSelected ? 3 : 1,
                  fillColor: health.color,
                  fillOpacity: dimmed ? 0.45 : 0.92,
                }}
                eventHandlers={{
                  click: () => onSelectSite?.(site.site),
                }}
              >
                <Popup>
                  <div className="max-w-[14rem] text-xs">
                    <p className="font-semibold text-veld-900">{site.site}</p>
                    {site.region && (
                      <p className="text-ink-muted">{site.region}</p>
                    )}
                    <p className="mt-1 font-semibold" style={{ color: health.color }}>
                      {health.label}
                    </p>
                    <p className="mt-0.5 text-ink-muted">{health.hint}</p>
                    <dl className="mt-2 space-y-0.5 text-ink">
                      <div className="flex justify-between gap-3">
                        <dt>Cover</dt>
                        <dd className="font-semibold">
                          {site.vegetation_cover != null
                            ? `${site.vegetation_cover}%`
                            : "n/a"}
                        </dd>
                      </div>
                      <div className="flex justify-between gap-3">
                        <dt>Greenness (NDVI)</dt>
                        <dd className="font-semibold">
                          {site.ndvi != null ? site.ndvi : "n/a"}
                        </dd>
                      </div>
                      <div className="flex justify-between gap-3">
                        <dt>Bush signal</dt>
                        <dd className="font-semibold">
                          {site.bush_encroachment != null
                            ? `${site.bush_encroachment}%`
                            : "n/a"}
                        </dd>
                      </div>
                    </dl>
                    <button
                      type="button"
                      className="mt-2 font-semibold text-veld-800"
                      onClick={() => onSelectSite?.(site.site)}
                    >
                      Use this site
                    </button>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>

      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-ink-muted">
        <LegendSwatch color="#16a34a" label="Looks grassy" />
        <LegendSwatch color="#65a30d" label="Fair" />
        <LegendSwatch color="#ca8a04" label="Patchy" />
        <LegendSwatch color="#ea580c" label="Thin grass" />
        <LegendSwatch color="#b91c1c" label="Very thin" />
        <LegendSwatch color="#a8a29e" label="Unknown" />
      </div>
      <p className="mt-1 text-[10px] text-ink-muted">
        Colours use satellite greenness (NDVI) when available, otherwise vegetation
        cover from the survey. Compare neighbouring dots — a cluster of orange/red
        means that stretch of veld is looking thinner.
      </p>
    </Card>
  );
}
