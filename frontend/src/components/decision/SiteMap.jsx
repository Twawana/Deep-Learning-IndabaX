import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { getRegions } from "../../services/api";
import { NAMIBIA_LOCATIONS } from "../../utils/constants";
import Card from "../Card";

function healthColour(cover, biomass) {
  if (cover == null && biomass == null) return "#78716c";
  if ((cover != null && cover < 15) || (biomass != null && biomass < 50)) return "#dc2626";
  if ((cover != null && cover < 25) || (biomass != null && biomass < 100)) return "#ea580c";
  if (cover != null && cover >= 35) return "#059669";
  return "#d97706";
}

function FitNamibia({ sites }) {
  const map = useMap();
  useEffect(() => {
    const pts = sites.filter((s) => s.latitude != null && s.longitude != null);
    if (!pts.length) {
      map.setView([-22.5, 17.5], 5);
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
  }, [map, sites]);
  return null;
}

export default function SiteMap({ selectedLocation, onSelectSite, decision }) {
  const [sites, setSites] = useState([]);
  const [error, setError] = useState(null);

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
        // Fallback to picker coordinates
        setSites(
          NAMIBIA_LOCATIONS.map((loc) => ({
            site: loc.mapsTo || loc.name,
            region: loc.region,
            latitude: loc.lat,
            longitude: loc.lon,
            vegetation_cover: null,
            biomass: null,
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
    const name = (selectedLocation || "").toLowerCase();
    return sites.find(
      (s) =>
        String(s.site).toLowerCase() === name ||
        String(s.site).toLowerCase().includes(name)
    );
  }, [sites, selectedLocation]);

  return (
    <Card title="Grazing map">
      <p className="mb-2 text-xs text-ink-muted">
        Satellite view of research sites. Tap a marker to update your grazing
        location and recommendation.
        {decision?.headline ? ` Current advice: ${decision.headline}.` : ""}
      </p>
      {error && <p className="mb-2 text-xs text-amber-800">{error}</p>}
      <div className="h-56 overflow-hidden rounded-xl ring-1 ring-veld-100">
        <MapContainer
          center={[-22.5, 17.5]}
          zoom={5}
          className="h-full w-full"
          scrollWheelZoom={false}
        >
          <TileLayer
            attribution='Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics'
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          />
          <FitNamibia sites={sites} />
          {sites.map((site) => {
            const colour = healthColour(site.vegetation_cover, site.biomass);
            const isSelected =
              selected && String(selected.site) === String(site.site);
            return (
              <CircleMarker
                key={`${site.site}-${site.latitude}-${site.longitude}`}
                center={[site.latitude, site.longitude]}
                radius={isSelected ? 10 : 7}
                pathOptions={{
                  color: "#fff",
                  weight: isSelected ? 2 : 1,
                  fillColor: colour,
                  fillOpacity: 0.9,
                }}
                eventHandlers={{
                  click: () => onSelectSite?.(site.site),
                }}
              >
                <Popup>
                  <div className="text-xs">
                    <p className="font-semibold">{site.site}</p>
                    {site.region && <p>{site.region}</p>}
                    <p>
                      Cover:{" "}
                      {site.vegetation_cover != null
                        ? `${site.vegetation_cover}%`
                        : "n/a"}
                    </p>
                    <button
                      type="button"
                      className="mt-1 font-semibold text-veld-800"
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
      <div className="mt-2 flex flex-wrap gap-2 text-[10px] text-ink-muted">
        <span>🟢 Healthier</span>
        <span>🟡 Moderate</span>
        <span>🟠 Stressed</span>
        <span>🔴 Poor</span>
        <span>⚪ Unknown</span>
      </div>
    </Card>
  );
}
