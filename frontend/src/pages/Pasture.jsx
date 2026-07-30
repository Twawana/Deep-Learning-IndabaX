import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import Card from "../components/Card";
import ErrorAlert from "../components/ErrorAlert";
import Loader from "../components/Loader";
import { useFarmContext } from "../context/FarmContext";
import {
  getPasture,
  getPastureAnalysis,
  getWeather,
} from "../services/api";
import { NAMIBIA_LOCATIONS } from "../utils/constants";
import { getErrorMessage } from "../utils/format";
import { buildPastureAnalysis } from "../utils/pastureAnalysis";

const TONE = {
  good: {
    badge: "bg-veld-100 text-veld-800",
    bar: "bg-veld-600",
  },
  fair: {
    badge: "bg-sun-100 text-sun-600",
    bar: "bg-sun-500",
  },
  poor: {
    badge: "bg-danger-bg text-danger",
    bar: "bg-danger",
  },
};

function levelTone(level) {
  const text = String(level || "").toLowerCase();
  if (!text || text === "—") return TONE.fair;
  if (text.includes("high") || text.includes("dry") || text.includes("poor")) {
    return TONE.poor;
  }
  if (text.includes("low") && !text.includes("medium")) return TONE.good;
  if (text.includes("good") || text.includes("near") || text.includes("normal")) {
    return TONE.good;
  }
  return TONE.fair;
}

function show(value, suffix = "") {
  if (value === null || value === undefined || value === "") return "—";
  return `${value}${suffix}`;
}

export default function Pasture() {
  const farm = useFarmContext();
  const [analysisPayload, setAnalysisPayload] = useState(null);
  const [pasture, setPasture] = useState(null);
  const [weather, setWeather] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showMap, setShowMap] = useState(false);

  const analysis = useMemo(
    () =>
      buildPastureAnalysis({
        analysis: analysisPayload,
        pasture,
        weather,
        farm,
      }),
    [analysisPayload, pasture, weather, farm]
  );

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    const locationQuery =
      farm.customLocation || farm.village || farm.location;

    const params = {
      location: locationQuery,
      nearest_town: farm.location,
      region: farm.region,
      camp_name: farm.campName || undefined,
      herd_size: farm.herdSize || undefined,
      livestock_type: farm.livestockType || undefined,
      village: farm.village || undefined,
      farm_notes: farm.farmNotes || undefined,
      lat: farm.lat,
      lon: farm.lon,
      days: 30,
    };

    try {
      // Prefer one backend analysis endpoint for the whole screen.
      const analysisResult = await getPastureAnalysis(params);
      setAnalysisPayload(analysisResult);
      setPasture(analysisResult?.pasture || analysisResult);
      setWeather(analysisResult?.weather || null);
    } catch (analysisError) {
      // Fallback: combine /pasture + /weather from the backend.
      try {
        const [pastureResult, weatherResult] = await Promise.allSettled([
          getPasture(locationQuery, {
            region: farm.region,
            camp_name: farm.campName || undefined,
            herd_size: farm.herdSize || undefined,
            lat: farm.lat,
            lon: farm.lon,
          }),
          getWeather(farm.lat, farm.lon, { days: 30 }),
        ]);

        setAnalysisPayload(null);

        if (pastureResult.status === "fulfilled") {
          setPasture(pastureResult.value);
        } else {
          setPasture(null);
        }

        if (weatherResult.status === "fulfilled") {
          setWeather(weatherResult.value);
        } else {
          setWeather(null);
        }

        if (pastureResult.status === "rejected") {
          setError(
            getErrorMessage(
              pastureResult.reason,
              "Could not load pasture data from the backend."
            )
          );
        } else if (weatherResult.status === "rejected") {
          setError(
            getErrorMessage(
              weatherResult.reason,
              "Pasture loaded, but weather data could not be fetched."
            )
          );
        }
      } catch (err) {
        setAnalysisPayload(null);
        setPasture(null);
        setWeather(null);
        setError(
          getErrorMessage(
            analysisError,
            "Could not load pasture analysis from the backend."
          )
        );
      }
    } finally {
      setIsLoading(false);
    }
  }, [farm]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const statusTone = TONE[analysis.status.tone] || TONE.fair;
  const pressureTone = levelTone(analysis.grazing.pressure);
  const rainTone = TONE[analysis.weather.tone] || levelTone(analysis.weather.label);
  const hasData = analysis.hasPastureData;

  return (
    <div className="space-y-4 pb-2">
      <header className="space-y-3">
        <div>
          <h2 className="font-display text-2xl font-bold text-veld-900">
            Check Pasture
          </h2>
          <p className="mt-1 text-sm text-ink-muted">
            Monitor your grazing land condition
          </p>
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2 rounded-2xl bg-white px-3.5 py-3 shadow-sm ring-1 ring-veld-100">
            <LocationPin />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-veld-900">
                {analysis.locationLabel}
              </p>
              <p className="truncate text-xs text-ink-muted">
                Near {farm.location}
              </p>
            </div>
          </div>
          <label className="block">
            <span className="mb-1.5 block px-1 text-xs font-medium text-ink-muted">
              Change nearest town
            </span>
            <select
              value={farm.location}
              onChange={(e) => farm.setLocationByName(e.target.value)}
              className="w-full rounded-2xl border border-veld-200 bg-white px-3.5 py-3 text-sm font-medium outline-none focus:border-veld-500"
            >
              {NAMIBIA_LOCATIONS.map((loc) => (
                <option key={loc.name} value={loc.name}>
                  {loc.name} ({loc.region})
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      {error && (
        <ErrorAlert message={error} onDismiss={() => setError(null)} />
      )}

      {isLoading ? (
        <Loader label="Loading pasture data…" />
      ) : !hasData ? (
        <Card>
          <p className="text-sm text-ink-muted">
            No pasture data yet. Check that the backend is running, then tap
            Refresh analysis.
          </p>
          <button
            type="button"
            onClick={refresh}
            className="mt-3 flex w-full items-center justify-center rounded-2xl bg-veld-800 py-3 text-sm font-semibold text-white"
          >
            Refresh analysis
          </button>
        </Card>
      ) : (
        <>
          <section className="overflow-hidden rounded-3xl bg-gradient-to-br from-veld-800 to-veld-950 p-5 text-white shadow-lg shadow-veld-900/20">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-veld-300">
                  Pasture health
                </p>
                <p className="mt-2 font-display text-5xl font-bold leading-none">
                  {analysis.score != null ? analysis.score : "—"}
                  <span className="text-2xl font-semibold text-veld-300">
                    /100
                  </span>
                </p>
              </div>
              {analysis.status.label && (
                <span
                  className={`rounded-full px-3 py-1.5 text-xs font-bold ${statusTone.badge}`}
                >
                  {analysis.status.label}
                </span>
              )}
            </div>
            {analysis.score != null && (
              <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-white/15">
                <div
                  className="h-full rounded-full bg-sun-400 transition-all duration-500"
                  style={{ width: `${Math.min(100, Math.max(0, analysis.score))}%` }}
                />
              </div>
            )}
            {analysis.status.explanation && (
              <p className="mt-4 text-sm leading-relaxed text-veld-100">
                {analysis.status.explanation}
              </p>
            )}
          </section>

          <section className="space-y-3">
            <h3 className="px-1 font-display text-lg font-semibold text-veld-900">
              Vegetation condition
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <MetricCard
                label="NDVI"
                value={show(analysis.vegetation.ndvi)}
                hint="Greenness"
                icon={<LeafIcon />}
              />
              <MetricCard
                label="Grass cover"
                value={show(analysis.vegetation.grassCover)}
                hint="Ground cover"
                icon={<CoverIcon />}
              />
              <MetricCard
                label="Grass biomass"
                value={show(analysis.vegetation.grassBiomass)}
                hint="Available feed"
                icon={<BiomassIcon />}
              />
              <MetricCard
                label="Bush encroachment"
                value={show(analysis.vegetation.bushEncroachment)}
                hint="Woody plants"
                icon={<BushIcon />}
                tone={levelTone(analysis.vegetation.bushEncroachment)}
              />
            </div>
          </section>

          <Card title="Grazing pressure">
            <div className="space-y-3">
              <Row
                label="Current grazing pressure"
                value={
                  analysis.grazing.pressure ? (
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-bold ${pressureTone.badge}`}
                    >
                      {analysis.grazing.pressure}
                    </span>
                  ) : (
                    "—"
                  )
                }
              />
              <Row
                label="Current herd size"
                value={
                  analysis.grazing.herdSize != null
                    ? `${analysis.grazing.herdSize} ${analysis.grazing.livestock || ""}`.trim()
                    : "—"
                }
              />
              <Row
                label="Recommended capacity"
                value={
                  analysis.grazing.capacity != null
                    ? `${analysis.grazing.capacity} ${analysis.grazing.livestock || ""}`.trim()
                    : "—"
                }
              />
              {analysis.grazing.warning && (
                <div
                  className={`rounded-2xl px-3.5 py-3 text-sm leading-relaxed ${
                    analysis.grazing.overCapacity
                      ? "bg-danger-bg text-danger"
                      : "bg-veld-50 text-veld-800"
                  }`}
                >
                  {analysis.grazing.warning}
                </div>
              )}
            </div>
          </Card>

          <Card title="Weather impact">
            {!analysis.hasWeatherData ? (
              <p className="text-sm text-ink-muted">
                Weather data was not returned by the backend.
              </p>
            ) : (
              <div className="space-y-3">
                <Row
                  label="Rainfall (last 30 days)"
                  value={
                    analysis.weather.recentRain != null
                      ? `${analysis.weather.recentRain} mm`
                      : "—"
                  }
                />
                <Row
                  label="Average rainfall"
                  value={
                    analysis.weather.averageRain != null
                      ? `${analysis.weather.averageRain} mm`
                      : "—"
                  }
                />
                <Row
                  label="Status"
                  value={
                    analysis.weather.label ? (
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-bold ${rainTone.badge}`}
                      >
                        {analysis.weather.label}
                      </span>
                    ) : (
                      "—"
                    )
                  }
                />
                {analysis.weather.explanation && (
                  <p className="rounded-2xl bg-mist px-3.5 py-3 text-sm leading-relaxed text-ink-muted">
                    {analysis.weather.explanation}
                  </p>
                )}
              </div>
            )}
          </Card>

          <section className="rounded-3xl bg-sun-100/80 p-5 ring-1 ring-sun-300/50">
            <div className="mb-2 flex items-center gap-2">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-veld-800 text-sun-300">
                <AdviceIcon />
              </span>
              <h3 className="font-display text-lg font-semibold text-veld-900">
                AI Pasture Advice
              </h3>
            </div>
            <p className="text-sm leading-relaxed text-ink">
              {analysis.advice ||
                "No AI advice returned yet. Tap Ask AI more for a recommendation."}
            </p>
          </section>

          <div className="grid gap-2.5">
            <Link
              to="/chat"
              className="flex w-full items-center justify-center rounded-2xl bg-veld-800 py-3.5 text-sm font-semibold text-white active:bg-veld-900"
            >
              Ask AI more
            </Link>
            <button
              type="button"
              onClick={() => setShowMap(true)}
              className="flex w-full items-center justify-center rounded-2xl border border-veld-200 bg-white py-3.5 text-sm font-semibold text-veld-800 active:bg-veld-50"
            >
              View farm map
            </button>
            <button
              type="button"
              onClick={refresh}
              disabled={isLoading}
              className="flex w-full items-center justify-center rounded-2xl border border-veld-200 bg-white py-3.5 text-sm font-semibold text-veld-800 active:bg-veld-50 disabled:opacity-60"
            >
              {isLoading ? "Refreshing…" : "Refresh analysis"}
            </button>
          </div>
        </>
      )}

      {showMap && (
        <MapSheet
          lat={farm.lat}
          lon={farm.lon}
          label={analysis.locationLabel}
          onClose={() => setShowMap(false)}
        />
      )}
    </div>
  );
}

function MetricCard({ label, value, hint, icon, tone }) {
  return (
    <div className="rounded-2xl bg-white p-3.5 shadow-sm ring-1 ring-veld-100">
      <div className="mb-2 flex items-center justify-between">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-veld-50 text-veld-700">
          {icon}
        </span>
        {tone && (
          <span className={`h-2 w-2 rounded-full ${tone.bar}`} aria-hidden />
        )}
      </div>
      <p className="text-xs font-medium text-ink-muted">{label}</p>
      <p className="mt-0.5 font-display text-xl font-bold text-veld-900">
        {value}
      </p>
      <p className="mt-0.5 text-[11px] text-ink-muted">{hint}</p>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-sm text-ink-muted">{label}</span>
      <span className="text-right text-sm font-semibold text-veld-900">
        {value}
      </span>
    </div>
  );
}

function MapSheet({ lat, lon, label, onClose }) {
  const mapSrc = `https://www.openstreetmap.org/export/embed.html?bbox=${
    Number(lon) - 0.35
  }%2C${Number(lat) - 0.25}%2C${Number(lon) + 0.35}%2C${
    Number(lat) + 0.25
  }&layer=mapnik&marker=${lat}%2C${lon}`;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-veld-950/45 p-3 sm:items-center">
      <div className="w-full max-w-md overflow-hidden rounded-3xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-veld-100 px-4 py-3">
          <div>
            <p className="font-display text-base font-semibold text-veld-900">
              Farm map
            </p>
            <p className="text-xs text-ink-muted">{label}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl px-3 py-1.5 text-sm font-semibold text-veld-800"
          >
            Close
          </button>
        </div>
        <iframe
          title="Farm map"
          src={mapSrc}
          className="h-72 w-full border-0"
          loading="lazy"
        />
      </div>
    </div>
  );
}

function LocationPin() {
  return (
    <svg className="h-5 w-5 shrink-0 text-veld-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
    </svg>
  );
}

function LeafIcon() {
  return (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3c4 3 7 8 7 12a7 7 0 11-14 0c0-2 1-5 3-7" />
      <path strokeLinecap="round" d="M12 21V10" />
    </svg>
  );
}

function CoverIcon() {
  return (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 17l4-8 4 5 4-7 6 10H3z" />
    </svg>
  );
}

function BiomassIcon() {
  return (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 20V10m4 10V6m4 14v-8" />
    </svg>
  );
}

function BushIcon() {
  return (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 20v-6m0 0c-3 0-5-2.5-5-5.5S9 3 12 5c3-2 5 .5 5 3.5S15 14 12 14z" />
    </svg>
  );
}

function AdviceIcon() {
  return (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v.01M9.09 9a3 3 0 115.82 1c0 1.5-1.5 2.2-2.41 2.8-.8.5-1.5 1-1.5 2.2" />
      <circle cx="12" cy="12" r="9" />
    </svg>
  );
}
