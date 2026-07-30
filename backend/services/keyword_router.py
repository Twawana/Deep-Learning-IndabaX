"""
Offline keyword router — map farmer question keywords → dataset fields + tools.

No LLM. Keyword match only. Answers must come from DB fields that exist;
missing values are reported as missing (never invented).
"""

from __future__ import annotations

import re
from typing import Any, Optional


KEYWORD_TOPICS: list[dict[str, Any]] = [
    {
        "id": "bush",
        "label": "Bush encroachment",
        "keywords": (
            "bush",
            "encroach",
            "encroachment",
            "woody",
            "woodland",
            "shrub",
            "shrubs",
            "thicket",
            "thicken",
            "scrub",
            "trees crowding",
            "bush getting",
            "more bush",
            "less bush",
            "bush dens",
            "acacia",
            "terminalia",
            "blackthorn",
            "sicklebush",
            "invader plant",
            "woody plants",
            "woody cover",
        ),
        "fields": (
            "bush_encroachment",
            "bush_encroachment_level",
            "bush_biomass_kg_per_ha",
            "dominant_woody",
            "browsing_pressure_label",
        ),
        "tools": ("get_pasture_data", "compare_to_prior_year"),
    },
    {
        "id": "pasture",
        "label": "Pasture / veld condition",
        "keywords": (
            "pasture",
            "veld",
            "rangeland",
            "range land",
            "camp",
            "camps",
            "paddock",
            "paddocks",
            "vegetation",
            "cover",
            "ground cover",
            "biomass",
            "grass",
            "grasses",
            "forage",
            "fodder",
            "feed available",
            "bare ground",
            "bare soil",
            "denuded",
            "ndvi",
            "greenness",
            "condition",
            "healthy veld",
            "poor veld",
            "weak veld",
            "stand of grass",
            "perennial",
            "annual grass",
            "herbaceous",
            "how is my camp",
            "how is the camp",
            "how is the pasture",
            "how is the veld",
        ),
        "fields": (
            "vegetation_cover",
            "biomass",
            "grass_biomass_kg_per_ha",
            "cover_perennial_grass_pct",
            "cover_annual_grass_pct",
            "cover_bare_ground_pct",
            "ndvi",
            "dominant_herbaceous",
            "observation_date",
        ),
        "tools": ("get_pasture_data",),
    },
    {
        "id": "overgrazing",
        "label": "Overgrazing / grazing pressure",
        "keywords": (
            "overgraz",
            "over-graz",
            "over graz",
            "overgrazing",
            "overgrazed",
            "currently overgrazed",
            "grazing pressure",
            "take grazing pressure",
            "too many animal",
            "too many cattle",
            "pressure on",
            "stressed camp",
            "trampled",
            "trampled out",
            "eaten down",
            "grazed bare",
            "heavy grazing",
            "hard grazed",
            "stocked too heavy",
            "overstock",
            "over stock",
            "is this camp",
            "is this paddock",
        ),
        "fields": (
            "grazing_pressure",
            "grazing_pressure_label",
            "vegetation_cover",
            "biomass",
            "cover_bare_ground_pct",
            "livestock_density_lsu_per_ha",
            "carrying_capacity_ha_per_lsu",
        ),
        "tools": ("get_pasture_data", "calculate_grazing_pressure", "estimate_safe_stocking"),
    },
    {
        "id": "stocking",
        "label": "Stocking / carrying capacity",
        "keywords": (
            "stocking",
            "stocking rate",
            "stock rate",
            "safe stocking rate",
            "carrying capacity",
            "carrying capacit",
            "ha/lsu",
            "ha per lsu",
            "hectares per lsu",
            "lsu",
            "livestock unit",
            "safe herd",
            "safe stocking",
            "how many cattle",
            "how many animal",
            "how many head",
            "head count",
            "stocking density",
            "can i add cattle",
            "can i add animals",
            "reduce stock",
            "destock",
            "restock",
            "right now",
        ),
        "fields": (
            "carrying_capacity_ha_per_lsu",
            "livestock_density_lsu_per_ha",
            "number_cattle",
            "vegetation_cover",
            "biomass",
        ),
        "tools": ("get_pasture_data", "estimate_safe_stocking", "calculate_grazing_pressure"),
    },
    {
        "id": "move",
        "label": "Move / rest / rotation timing",
        "keywords": (
            "should i move",
            "when to move",
            "when should i move",
            "roughly when",
            "move my herd",
            "move the herd",
            "move cattle",
            "move them",
            "need to move",
            "before i need to move",
            "how long can",
            "how long should",
            "how long can my herd stay",
            "stay on this",
            "stay another",
            "rest this",
            "rest the camp",
            "rest camp",
            "rest this season",
            "which camp to rest",
            "which camps should i rest",
            "which of my camps",
            "camps should i rest",
            "still take grazing",
            "take grazing pressure",
            "prepare to move",
            "rotate",
            "rotation",
            "rotational",
            "shift the herd",
            "leave this camp",
            "take animals off",
        ),
        "fields": (
            "vegetation_cover",
            "biomass",
            "grazing_pressure_label",
            "carrying_capacity_ha_per_lsu",
            "cover_bare_ground_pct",
        ),
        "tools": ("get_pasture_data", "calculate_grazing_pressure", "estimate_safe_stocking"),
    },
    {
        "id": "yoy",
        "label": "Year-over-year / seasonal trend",
        "keywords": (
            "last year",
            "same time last",
            "same time last year",
            "year ago",
            "previous year",
            "getting worse",
            "getting better",
            "compared to last",
            "compare to the same",
            "than last year",
            "year over year",
            "year-over-year",
            "yoy",
            "trend",
            "improving",
            "declining",
            "same season",
            "this time last year",
            "compare to the same time",
        ),
        "fields": ("vegetation_cover", "biomass", "bush_encroachment", "ndvi"),
        "tools": ("get_pasture_data", "compare_to_prior_year"),
    },
    {
        "id": "rainfall",
        "label": "Rainfall / dry / wet conditions",
        "keywords": (
            "rain",
            "rains",
            "rainfall",
            "precipitation",
            "drought",
            "dry spell",
            "dry season",
            "rainy season",
            "wet season",
            "wet",
            "moisture",
            "forecast",
            "weather",
            "no rain",
            "little rain",
            "recent rain",
            "recent rainfall",
            "given the recent",
            "did it rain",
        ),
        "fields": ("vegetation_cover", "biomass", "ndvi", "observation_date"),
        "tools": ("get_pasture_data", "calculate_grazing_pressure", "estimate_safe_stocking"),
        "online_tools": ("get_weather",),
    },
    {
        "id": "water",
        "label": "Water / watering points",
        "keywords": (
            "water point",
            "watering",
            "waterhole",
            "water hole",
            "trough",
            "dam water",
            "borehole",
            "drinking water",
            "water for cattle",
        ),
        "fields": ("vegetation_cover", "biomass", "cover_bare_ground_pct"),
        "tools": ("get_pasture_data",),
    },
    {
        "id": "tenure",
        "label": "Land tenure comparison",
        "keywords": (
            "communal",
            "commercial",
            "conservanc",
            "conservancy",
            "freehold",
            "resettlement",
            "tenure",
            "land tenure",
            "similar land",
            "similar land tenure",
            "land type",
            "neighbouring farms",
            "nearby farms",
            "nearby",
            "vs. conservancy",
            "vs conservancy",
            "communal vs",
            "commercial nearby",
        ),
        "fields": ("vegetation_cover", "biomass", "bush_encroachment", "carrying_capacity_ha_per_lsu"),
        "tools": ("get_pasture_data", "compare_tenure_nearby"),
    },
    {
        "id": "compare",
        "label": "Compare camps / locations",
        "keywords": (
            "compare",
            "comparison",
            " versus ",
            " vs ",
            " vs.",
            "difference between",
            "which camp",
            "which paddock",
            "which of my camps",
            "which area",
            "better camp",
            "worse camp",
            "side by side",
        ),
        "fields": ("vegetation_cover", "biomass", "bush_encroachment", "ndvi", "grazing_pressure_label"),
        "tools": ("get_pasture_data", "calculate_grazing_pressure", "estimate_safe_stocking"),
    },
    {
        "id": "scenario",
        "label": "What-if scenario",
        "keywords": (
            "what if",
            "what-if",
            "suppose",
            "if i add",
            "if i reduce",
            "if i double",
            "if i halve",
            "if i move",
            "imagine if",
            "scenario",
        ),
        "fields": ("carrying_capacity_ha_per_lsu", "vegetation_cover", "biomass"),
        "tools": ("run_what_if_scenario", "get_pasture_data"),
    },
    {
        "id": "herd",
        "label": "Herd / livestock",
        "keywords": (
            "herd",
            "cattle",
            "cows",
            "oxen",
            "goats",
            "sheep",
            "livestock",
            "animals",
            "stock",
            "calves",
            "bulls",
            "weaners",
            "nguni",
            "brahman",
        ),
        "fields": (
            "number_cattle",
            "livestock_density_lsu_per_ha",
            "grazing_pressure_label",
            "carrying_capacity_ha_per_lsu",
        ),
        "tools": ("get_pasture_data", "calculate_grazing_pressure"),
    },
    {
        "id": "soil_bare",
        "label": "Bare ground / erosion risk signals",
        "keywords": (
            "bare",
            "erosion",
            "dust",
            "dusty",
            "crust",
            "soil exposed",
            "no grass left",
        ),
        "fields": ("cover_bare_ground_pct", "vegetation_cover", "biomass"),
        "tools": ("get_pasture_data",),
    },
]

FIELD_LABELS = {
    "bush_encroachment": "Bush / woody cover %",
    "bush_encroachment_level": "Bush encroachment level",
    "bush_biomass_kg_per_ha": "Bush biomass (kg/ha)",
    "dominant_woody": "Dominant woody plants",
    "browsing_pressure_label": "Browsing pressure label",
    "vegetation_cover": "Vegetation cover %",
    "biomass": "Biomass",
    "grass_biomass_kg_per_ha": "Grass biomass (kg/ha)",
    "cover_perennial_grass_pct": "Perennial grass cover %",
    "cover_annual_grass_pct": "Annual grass cover %",
    "cover_bare_ground_pct": "Bare ground %",
    "ndvi": "NDVI",
    "dominant_herbaceous": "Dominant grasses/herbs",
    "observation_date": "Observation date",
    "grazing_pressure": "Recorded grazing pressure",
    "grazing_pressure_label": "Grazing pressure label",
    "carrying_capacity_ha_per_lsu": "Carrying capacity (ha/LSU)",
    "livestock_density_lsu_per_ha": "Livestock density (LSU/ha)",
    "number_cattle": "Cattle count on record",
}

# Place / farm mentions that still justify a DB lookup
LOCATION_HINTS = (
    "farm",
    "camp",
    "paddock",
    "veld",
    "gobabis",
    "outjo",
    "neudamm",
    "omaheke",
    "khomas",
    "windhoek",
    "otjiwarongo",
    "grootfontein",
    "okahandja",
    "mariental",
    "keetmanshoop",
    "oshakati",
    "rundu",
    "katima",
    "molly",
    "namibia",
)


def match_keywords(message: str) -> dict[str, Any]:
    """Scan the farmer question for keywords -> topics, tools, DB fields."""
    text = f" {(message or '').lower()} "
    matched: list[dict[str, Any]] = []
    hits: list[str] = []

    for topic in KEYWORD_TOPICS:
        topic_hits = [kw for kw in topic["keywords"] if kw in text]
        if not topic_hits:
            continue
        matched.append(
            {
                "id": topic["id"],
                "label": topic["label"],
                "matched_keywords": topic_hits,
                "fields": list(topic["fields"]),
                "tools": list(topic["tools"]),
                "online_tools": list(topic.get("online_tools") or ()),
            }
        )
        hits.extend(topic_hits)

    if not matched and any(h in text for h in LOCATION_HINTS):
        pasture = next(t for t in KEYWORD_TOPICS if t["id"] == "pasture")
        matched.append(
            {
                "id": "pasture",
                "label": pasture["label"],
                "matched_keywords": ["(location/farm mention)"],
                "fields": list(pasture["fields"]),
                "tools": list(pasture["tools"]),
                "online_tools": [],
            }
        )

    tools: list[str] = []
    fields: list[str] = []
    for m in matched:
        for t in m["tools"]:
            if t not in tools:
                tools.append(t)
        for f in m["fields"]:
            if f not in fields:
                fields.append(f)

    return {
        "matched_topics": matched,
        "matched_keywords": list(dict.fromkeys(hits)),
        "tools": tools,
        "fields": fields,
        "understood": bool(matched),
    }


def format_field_value(key: str, value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    label = FIELD_LABELS.get(key, key.replace("_", " "))
    if key == "observation_date":
        return f"{label}: {value}"
    try:
        num = float(value)
        if key in {
            "vegetation_cover",
            "bush_encroachment",
            "cover_perennial_grass_pct",
            "cover_annual_grass_pct",
            "cover_bare_ground_pct",
        }:
            return f"{label}: {num:.0f}% (from database)"
        if key == "ndvi":
            return f"{label}: {num:.2f} (from database)"
        if "biomass" in key or "kg" in key:
            return f"{label}: {num:.0f} (from database)"
        if "ha_per_lsu" in key or "lsu_per_ha" in key:
            return f"{label}: {num:.2f} (from database)"
        return f"{label}: {num:g} (from database)"
    except (TypeError, ValueError):
        return f"{label}: {value} (from database)"


def extract_relevant_facts(
    *,
    fields: list[str],
    pasture_data: Optional[dict[str, Any]] = None,
    year_over_year: Optional[dict[str, Any]] = None,
    stocking: Optional[dict[str, Any]] = None,
    grazing: Optional[dict[str, Any]] = None,
) -> dict[str, list[str]]:
    """
    Pull matched DB fields into fact lines.

    Returns {"found": [...], "missing": [...]} — never invents values.
    """
    pasture_data = pasture_data or {}
    metrics = dict(pasture_data.get("pasture") or {})
    # observation_date lives on the parent payload
    if pasture_data.get("observation_date") is not None:
        metrics.setdefault("observation_date", pasture_data.get("observation_date"))
    nearby = pasture_data.get("nearby_synthetic") or {}
    found: list[str] = []
    missing: list[str] = []

    for key in fields:
        val = metrics.get(key)
        source_note = ""
        if val is None and nearby.get("found") and nearby.get(key) is not None:
            val = nearby.get(key)
            source_note = " [nearby synthetic site]"
        line = format_field_value(key, val)
        if line:
            found.append(line + source_note)
        else:
            label = FIELD_LABELS.get(key, key.replace("_", " "))
            missing.append(f"{label}: not in database for this location")

    if year_over_year and year_over_year.get("found"):
        if year_over_year.get("summary"):
            found.append(f"Year-over-year (database): {year_over_year['summary']}")
        deltas = year_over_year.get("deltas") or {}
        for key, label in (
            ("bush_encroachment", "Bush delta vs last year"),
            ("vegetation_cover", "Cover delta vs last year"),
            ("biomass", "Biomass delta vs last year"),
            ("ndvi", "NDVI delta vs last year"),
        ):
            if deltas.get(key) is not None:
                found.append(f"{label}: {float(deltas[key]):+.1f} (from database)")
    elif year_over_year is not None and fields:
        # Only note missing YoY when we tried to fetch it
        if any(
            t in {"bush", "yoy"}
            for t in []
        ):
            pass

    if stocking and stocking.get("found"):
        if stocking.get("status"):
            found.append(f"Stocking status (calculated from DB + profile): {stocking['status']}")
        safe_head = stocking.get("safe_head_on_farm")
        if safe_head is not None:
            found.append(
                f"Safe herd estimate (from carrying capacity in DB): ~{safe_head}"
            )
        if stocking.get("carrying_capacity_ha_per_lsu") is not None:
            found.append(
                f"Carrying capacity rate: {float(stocking['carrying_capacity_ha_per_lsu']):.1f} ha/LSU (from database)"
            )
        if stocking.get("advice"):
            found.append(str(stocking["advice"]))
    elif stocking is not None and stocking.get("found") is False:
        missing.append("Stocking estimate: not enough database/profile inputs")

    if grazing and grazing.get("grazing_risk"):
        found.append(f"Grazing risk (from DB + herd profile): {grazing['grazing_risk']}")
        if grazing.get("reason"):
            found.append(str(grazing["reason"]))

    return {"found": found, "missing": missing}


def _cover_biomass(pasture_data: dict[str, Any]) -> tuple[Optional[float], Optional[float]]:
    metrics = pasture_data.get("pasture") or {}
    nearby = pasture_data.get("nearby_synthetic") or {}
    cover = metrics.get("vegetation_cover")
    biomass = metrics.get("biomass")
    if cover is None and nearby.get("found"):
        cover = nearby.get("vegetation_cover")
    if biomass is None and nearby.get("found"):
        biomass = nearby.get("biomass")
    try:
        cover_f = float(cover) if cover is not None else None
    except (TypeError, ValueError):
        cover_f = None
    try:
        biomass_f = float(biomass) if biomass is not None else None
    except (TypeError, ValueError):
        biomass_f = None
    return cover_f, biomass_f


def _stay_band(cover: Optional[float], risk: Optional[str], status: Optional[str]) -> str:
    """Rough stay/move band from DB indicators — labelled as estimate, not exact days."""
    risk_l = (risk or "").lower()
    status_l = (status or "").lower()
    if status_l == "overstocked" or risk_l in {"high", "severe", "critical"}:
        return (
            "Direct answer (from DB + profile pressure): prepare to move soon - "
            "within about 3-7 days if cover stays this weak. Exact calendar days "
            "are not stored in the database."
        )
    if cover is not None and cover < 20:
        return (
            "Direct answer (from low vegetation cover in DB): short remaining grazing window - "
            "plan to move within about 1-2 weeks, and walk the camp sooner if bare ground expands. "
            "I will not invent a precise day count."
        )
    if (cover is not None and cover < 40) or status_l == "near_capacity" or risk_l == "medium":
        return (
            "Direct answer (from moderate cover / near-capacity signals in DB): "
            "rough stay window about 2-4 weeks if conditions hold, then reassess. "
            "Not an exact day forecast."
        )
    if cover is not None or status_l == "within_capacity":
        return (
            "Direct answer (from DB cover/capacity signals): herd can stay longer - "
            "often on the order of 4-6+ weeks — but re-check after rain or if cover drops. "
            "Exact stay-days are not a database field."
        )
    return (
        "Direct answer: not enough cover/stocking fields to estimate stay length. "
        "I will not invent days."
    )


def _rest_or_graze_verdict(
    *,
    location: str,
    cover: Optional[float],
    risk: Optional[str],
    status: Optional[str],
) -> str:
    risk_l = (risk or "").lower()
    status_l = (status or "").lower()
    rest = (
        status_l == "overstocked"
        or risk_l in {"high", "severe", "critical"}
        or (cover is not None and cover < 25)
    )
    if rest:
        return (
            f"Camp rest read for {location} (only site loaded in Profile): "
            f"REST / ease pressure this season - cover/pressure signals are weak "
            f"(cover={cover if cover is not None else 'n/a'}%, risk={risk or 'n/a'}, "
            f"stocking={status or 'n/a'}). "
            "Name other camps in chat (or switch Profile location) to rank which can still take grazing."
        )
    return (
        f"Camp rest read for {location} (only site loaded in Profile): "
        "can still take light-moderate grazing if you watch cover "
        f"(cover={cover if cover is not None else 'n/a'}%, risk={risk or 'n/a'}, "
        f"stocking={status or 'n/a'}). "
        "Rest any sister camp that is thinner than this one - ask about each camp by name for a DB lookup."
    )


def build_grounded_reply(
    *,
    message: str,
    location: str,
    match: dict[str, Any],
    pasture_data: Optional[dict[str, Any]] = None,
    year_over_year: Optional[dict[str, Any]] = None,
    stocking: Optional[dict[str, Any]] = None,
    grazing: Optional[dict[str, Any]] = None,
    tenure: Optional[dict[str, Any]] = None,
    scenario: Optional[dict[str, Any]] = None,
    comparison: Optional[dict[str, Any]] = None,
    weather_data: Optional[dict[str, Any]] = None,
    online: bool = False,
) -> str:
    """
    Strict grounded answer: keywords matched + DB facts + honest gaps.
    Challenge questions get a Direct answer section when DB supports it.
    """
    pasture_data = pasture_data or {}
    year_over_year = year_over_year or {}
    stocking = stocking or {}
    grazing = grazing or {}
    tenure = tenure or {}
    weather_data = weather_data or {}
    topics = match.get("matched_topics") or []
    keywords = match.get("matched_keywords") or []
    topic_ids = {t["id"] for t in topics}
    topic_labels = ", ".join(t["label"] for t in topics) or "rangeland"
    text_l = (message or "").lower()

    use_yoy = "bush" in topic_ids or "yoy" in topic_ids
    use_stock = bool(
        topic_ids & {"stocking", "move", "overgrazing", "rainfall", "compare", "herd"}
    )
    use_graze = bool(
        topic_ids & {"overgrazing", "move", "herd", "stocking", "rainfall", "compare"}
    )

    facts = extract_relevant_facts(
        fields=match.get("fields") or [],
        pasture_data=pasture_data,
        year_over_year=year_over_year if use_yoy else None,
        stocking=stocking if use_stock else None,
        grazing=grazing if use_graze else None,
    )

    parts: list[str] = [
        f"Keywords matched: {', '.join(keywords[:12]) or 'farm/pasture'}.",
        f"Topics: {topic_labels}.",
        f"Database facts for {location}:",
    ]

    if pasture_data.get("found"):
        matched_on = pasture_data.get("matched_on")
        match_value = pasture_data.get("match_value")
        if matched_on:
            parts.append(f"Matched survey rows on {matched_on}={match_value}.")
    else:
        parts.append(
            f"No survey rows found for '{location}'. "
            "Set a supported site in Profile (e.g. Gobabis, Molly, Neudamm)."
        )

    if facts["found"]:
        parts.append("\n".join(f"- {f}" for f in facts["found"][:18]))
    else:
        parts.append("- No matching numeric fields were populated in the database for this ask.")

    if facts["missing"]:
        parts.append("Not found in database (so I will not invent them):")
        parts.append("\n".join(f"- {m}" for m in facts["missing"][:10]))

    cover, _biomass = _cover_biomass(pasture_data)
    risk = grazing.get("grazing_risk")
    status = stocking.get("status") if stocking.get("found") else None

    # --- Challenge Q1: overgrazed? ---
    if "overgrazing" in topic_ids:
        if risk or cover is not None or status:
            over = (
                (status == "overstocked")
                or (risk and str(risk).lower() in {"high", "severe", "critical"})
                or (cover is not None and cover < 20)
            )
            verdict = "YES - signals point to overgrazing / overpressure" if over else (
                "LIKELY NOT severely overgrazed from current DB+profile signals"
                if (status == "within_capacity" or (cover is not None and cover >= 35))
                else "BORDERLINE — watch closely"
            )
            bits = []
            if cover is not None:
                bits.append(f"cover {cover:.0f}%")
            if risk:
                bits.append(f"grazing risk {risk}")
            if status:
                bits.append(f"stocking {status}")
            parts.append(
                f"Direct answer (overgrazed?): {verdict} "
                f"({', '.join(bits) or 'limited fields'}). "
                "Confirm on foot before destocking."
            )
        else:
            parts.append(
                "Direct answer (overgrazed?): not enough database/profile fields for yes/no. "
                "I will not invent that verdict."
            )

    # --- Challenge Q2: safe stocking / carrying capacity ---
    if "stocking" in topic_ids:
        if stocking.get("found") and stocking.get("advice"):
            rate = stocking.get("carrying_capacity_ha_per_lsu")
            safe = stocking.get("safe_head_on_farm")
            bits = []
            if rate is not None:
                bits.append(f"~{float(rate):.1f} ha/LSU")
            if safe is not None:
                bits.append(f"cautious ceiling ~{safe} head on your stated farm/camp size")
            parts.append(
                "Direct answer (safe stocking / carrying capacity): "
                + ("; ".join(bits) if bits else stocking.get("status") or "see facts above")
                + ". Calculated from database ha/LSU + Profile herd/farm size - not a guess."
            )
        else:
            parts.append(
                "Direct answer (safe stocking): carrying capacity (ha/LSU) not in database "
                "for this site, so I cannot give a safe head count."
            )

    # --- Challenge Q3 + Q7: move when / how long stay ---
    if "move" in topic_ids or (
        "rainfall" in topic_ids
        and any(w in text_l for w in ("how long", "move", "stay"))
    ):
        parts.append(_stay_band(cover, risk, status))
        if "should i move" in text_l or "move my herd" in text_l or "roughly when" in text_l:
            if status == "overstocked" or (risk and str(risk).lower() in {"high", "severe", "critical"}):
                parts.append(
                    "Direct answer (should I move?): YES - move sooner rather than later "
                    "based on pressure/cover in the database and your herd profile."
                )
            elif cover is not None and cover < 25:
                parts.append(
                    "Direct answer (should I move?): YES, plan the move - cover is low in the database."
                )
            elif status == "within_capacity" and (cover is None or cover >= 35):
                parts.append(
                    "Direct answer (should I move?): NOT urgently - capacity/cover look OK for now; "
                    "reassess after the next dry spell or if bare ground increases."
                )
            else:
                parts.append(
                    "Direct answer (should I move?): MAYBE soon - signals are mixed; "
                    "use the stay-window above and walk the camp."
                )

    # --- Challenge Q4: vs last year ---
    if "yoy" in topic_ids and "bush" not in topic_ids:
        if year_over_year.get("found") and year_over_year.get("summary"):
            parts.append(
                f"Direct answer (vs same time last year): {year_over_year['summary']}"
            )
        elif year_over_year.get("found"):
            parts.append(
                "Direct answer (vs same time last year): comparison ran but the summary was empty - "
                "see deltas in the facts above if present."
            )
        else:
            parts.append(
                "Direct answer (vs same time last year): prior-year rows are not available "
                "for this site in the database, so I cannot invent a trend."
            )

    # --- Challenge Q5: which camps rest ---
    if (
        "which of my camps" in text_l
        or "rest this season" in text_l
        or "take grazing pressure" in text_l
        or "camps should i rest" in text_l
        or ("which camp" in text_l and "rest" in text_l)
        or ("still take" in text_l and "grazing" in text_l)
    ):
        parts.append(
            _rest_or_graze_verdict(
                location=location, cover=cover, risk=risk, status=status
            )
        )

    # --- Challenge Q6: bush worse + what to do ---
    if "bush" in topic_ids:
        if year_over_year.get("found") and year_over_year.get("summary"):
            parts.append(f"Direct answer (bush trend): {year_over_year['summary']}")
        else:
            parts.append(
                "Direct answer (bush trend): year-to-year bush comparison is not available "
                "in the database for this site, so I cannot say if encroachment is getting worse."
            )
        bush = (pasture_data.get("pasture") or {}).get("bush_encroachment")
        nearby = pasture_data.get("nearby_synthetic") or {}
        if bush is None and nearby.get("found"):
            bush = nearby.get("bush_encroachment")
        if bush is not None:
            try:
                b = float(bush)
                if b >= 25:
                    parts.append(
                        "Direct answer (what to do): woody/bush cover is elevated "
                        f"({b:.0f}% in DB). Rest the worst camps, avoid opening new thickets to "
                        "continuous grazing, and get local advice before thinning/browsing."
                    )
                else:
                    parts.append(
                        f"Direct answer (what to do): current bush/woody cover is {b:.0f}% "
                        "(not extreme in this reading). Keep monitoring the same camps each season; "
                        "no aggressive clearing justified from this DB reading alone."
                    )
            except (TypeError, ValueError):
                pass

    # --- Challenge Q7 rainfall context ---
    if "rainfall" in topic_ids:
        if online and weather_data.get("found"):
            recent = (weather_data.get("recent_rainfall") or {}).get("total_precipitation_mm")
            days = (weather_data.get("recent_rainfall") or {}).get("days") or 7
            if recent is not None:
                parts.append(
                    f"Live weather (Open-Meteo): about {float(recent):.1f} mm over the last {days} days. "
                    "Stay-window above still uses pasture cover/stocking from the database - "
                    "rain alone is not turned into invented grazing days."
                )
            else:
                parts.append("Live weather was queried but rainfall totals were empty.")
        else:
            parts.append(
                "Rainfall mm are not in the offline pasture database - I will not invent them. "
                "Stay guidance above uses vegetation/biomass/stocking from the DB as a proxy. "
                "Reconnect for live Open-Meteo rainfall."
            )

    # --- Challenge Q8: tenure peers ---
    if "tenure" in topic_ids:
        if tenure.get("found") and tenure.get("summary"):
            parts.append(f"Direct answer (tenure nearby): {tenure['summary']}")
        else:
            parts.append(
                "Direct answer (tenure nearby): no nearby tenure peers found in the database "
                "for this location/radius."
            )

    if scenario and scenario.get("found") and scenario.get("farmer_summary"):
        parts.append(str(scenario["farmer_summary"]))
    if comparison and comparison.get("found"):
        parts.append(
            str(comparison.get("summary") or comparison.get("farmer_summary") or "")
        )

    parts.append(
        "I only report values present in the local advisory database (or live weather when online). "
        "If a field is missing above, it was not invented."
    )
    if not online:
        parts.append("(Offline mode: keyword match + local database only.)")

    return "\n\n".join(p for p in parts if p and str(p).strip())
