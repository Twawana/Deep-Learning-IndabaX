/**
 * Map backend pasture + weather payloads into the Pasture screen model.
 * Does not invent demo values — missing fields stay null / empty.
 */

function pick(...values) {
  for (const value of values) {
    if (value !== null && value !== undefined && value !== "") return value;
  }
  return null;
}

function toNumber(value) {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "number" && !Number.isNaN(value)) return value;
  const parsed = parseFloat(String(value).replace(/[^\d.-]/g, ""));
  return Number.isNaN(parsed) ? null : parsed;
}

function toText(value) {
  if (value === null || value === undefined || value === "") return null;
  return String(value);
}

function toPercentDisplay(value) {
  if (value === null || value === undefined || value === "") return null;
  const text = String(value);
  if (text.includes("%")) return text;
  const num = toNumber(value);
  return num == null ? text : `${Math.round(num)}%`;
}

function normalizeLevel(value) {
  const text = toText(value);
  if (!text) return null;
  const lower = text.toLowerCase();
  if (/(low|light|minimal)/.test(lower)) return "Low";
  if (/(high|severe|heavy|critical)/.test(lower)) return "High";
  if (/(medium|moderate|fair|average|low\/medium)/.test(lower)) {
    if (lower.includes("low") && lower.includes("medium")) return "Low/Medium";
    return "Medium";
  }
  return text;
}

function toneFromStatus(label) {
  const text = String(label || "").toLowerCase();
  if (/(good|healthy|near normal|normal|low)/.test(text) && !/(below|poor|high)/.test(text)) {
    return "good";
  }
  if (/(poor|critical|very dry|needs attention|high|severe)/.test(text)) {
    return "poor";
  }
  return "fair";
}

function display(value, suffix = "") {
  if (value === null || value === undefined || value === "") return "—";
  return `${value}${suffix}`;
}

/**
 * Prefer a dedicated analysis payload from GET /pasture/analysis.
 * Falls back to combining GET /pasture + GET /weather.
 */
export function buildPastureAnalysis({ analysis, pasture, weather, farm }) {
  const source = analysis || {};
  const pastureData = pasture || source.pasture || {};
  const weatherData = weather || source.weather || {};

  const healthBlock = source.health || {};
  const vegetationBlock = source.vegetation || {};
  const grazingBlock = source.grazing || {};
  const weatherBlock = source.weather_impact || source.rainfall || {};

  const score = toNumber(
    pick(healthBlock.score, source.health_score, pastureData.health_score, pastureData.pasture_health_score)
  );

  const statusLabel = toText(
    pick(
      healthBlock.status,
      healthBlock.label,
      source.status,
      pastureData.condition,
      pastureData.status
    )
  );

  const statusExplanation = toText(
    pick(
      healthBlock.explanation,
      healthBlock.summary,
      source.explanation,
      pastureData.summary,
      pastureData.status_explanation
    )
  );

  const ndvi = toNumber(pick(vegetationBlock.ndvi, pastureData.ndvi));
  const grassCover = toPercentDisplay(
    pick(
      vegetationBlock.grass_cover,
      vegetationBlock.vegetation_cover,
      pastureData.grass_cover,
      pastureData.vegetation_cover
    )
  );
  const grassBiomass = toText(
    pick(vegetationBlock.grass_biomass, pastureData.grass_biomass, pastureData.biomass)
  );
  const bushEncroachment = normalizeLevel(
    pick(
      vegetationBlock.bush_encroachment,
      pastureData.bush_encroachment
    )
  ) || toText(pick(vegetationBlock.bush_encroachment, pastureData.bush_encroachment));

  const pressure = normalizeLevel(
    pick(grazingBlock.pressure, grazingBlock.grazing_pressure, pastureData.grazing_pressure)
  ) || toText(pick(grazingBlock.pressure, pastureData.grazing_pressure));

  const herdSize = toNumber(
    pick(grazingBlock.herd_size, grazingBlock.current_herd_size, farm?.herdSize)
  );

  const livestock = toText(
    pick(
      grazingBlock.livestock_type,
      grazingBlock.livestock,
      farm?.livestockType,
      "cattle"
    )
  );

  const capacity = toNumber(
    pick(
      grazingBlock.recommended_capacity,
      grazingBlock.carrying_capacity,
      pastureData.recommended_capacity,
      pastureData.carrying_capacity,
      pastureData.recommended_herd_size
    )
  );

  const overCapacity =
    herdSize != null && capacity != null ? herdSize > capacity : null;

  const grazingWarning = toText(
    pick(
      grazingBlock.warning,
      grazingBlock.message,
      overCapacity === true
        ? "Your livestock numbers are above the estimated carrying capacity."
        : overCapacity === false
          ? "Your livestock numbers are within the estimated carrying capacity."
          : null
    )
  );

  const recentRain = toNumber(
    pick(
      weatherBlock.rainfall_last_30_days,
      weatherBlock.recent_rainfall_mm,
      weatherData.rainfall_last_30_days,
      weatherData.recent_rainfall_mm
    )
  );

  const averageRain = toNumber(
    pick(
      weatherBlock.average_rainfall,
      weatherBlock.average_rainfall_30_days,
      weatherData.average_rainfall,
      weatherData.average_rainfall_30_days
    )
  );

  const weatherStatus = toText(
    pick(
      weatherBlock.status,
      weatherBlock.drought_indicator,
      weatherData.drought_indicator,
      weatherData.rainfall_status
    )
  );

  const weatherExplanation = toText(
    pick(
      weatherBlock.explanation,
      weatherBlock.summary,
      weatherData.rainfall_explanation,
      weatherData.summary
    )
  );

  const advice = toText(
    pick(
      source.ai_advice,
      source.recommendation,
      source.ai_recommendation,
      Array.isArray(source.recommendations) ? source.recommendations[0] : null,
      pastureData.ai_advice,
      pastureData.ai_recommendation,
      pastureData.recommendation
    )
  );

  const campName = toText(pick(source.camp_name, farm?.campName));
  const region = toText(pick(source.region, pastureData.region, farm?.region));
  const nearestTown = toText(
    pick(source.nearest_town, source.location, pastureData.location, farm?.location)
  );

  const locationLabel = toText(
    pick(
      source.location_label,
      region && campName
        ? `${region} — ${campName}`
        : region && nearestTown
          ? `${region} — ${nearestTown}`
          : campName
            ? `${nearestTown || "Farm"} — ${campName}`
            : nearestTown
    )
  );

  return {
    hasPastureData: Boolean(analysis || pasture),
    hasWeatherData: Boolean(
      analysis?.weather_impact ||
        analysis?.rainfall ||
        analysis?.weather ||
        weather
    ),
    locationLabel: locationLabel || "Your farm",
    region,
    campName,
    nearestTown,
    score,
    status: {
      label: statusLabel,
      tone: toneFromStatus(statusLabel),
      explanation: statusExplanation,
    },
    vegetation: {
      ndvi: ndvi == null ? null : Number(ndvi.toFixed(2)),
      grassCover,
      grassBiomass,
      bushEncroachment,
    },
    grazing: {
      pressure,
      herdSize,
      livestock,
      capacity,
      overCapacity,
      warning: grazingWarning,
    },
    weather: {
      recentRain,
      averageRain,
      label: weatherStatus,
      tone: toneFromStatus(weatherStatus),
      explanation: weatherExplanation,
    },
    advice,
    display,
  };
}
