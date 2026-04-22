from __future__ import annotations

import html as html_lib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and not math.isnan(float(value))


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if _is_number(value):
        return float(value)
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _round(value: float | None, digits: int = 2) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def _to_mg(value: float, unit: str) -> float | None:
    unit = (unit or "").strip().lower()
    if unit in {"mg", "milligram", "milligrams"}:
        return value
    if unit in {"µg", "μg", "Âµg", "ug", "mcg", "microgram", "micrograms"}:
        return value / 1000.0
    if unit in {"g", "gram", "grams"}:
        return value * 1000.0
    return None


def _to_mcg(value: float, unit: str) -> float | None:
    unit = (unit or "").strip().lower()
    if unit in {"µg", "μg", "Âµg", "ug", "mcg", "microgram", "micrograms"}:
        return value
    if unit in {"mg", "milligram", "milligrams"}:
        return value * 1000.0
    if unit in {"g", "gram", "grams"}:
        return value * 1_000_000.0
    return None


@dataclass(frozen=True)
class NutritionFetchResult:
    calories_kcal: float | None
    energy_basis: str | None  # "serving" | "100g"
    macros: dict[str, float | None]
    vitamins: dict[str, float | None]
    minerals: dict[str, float | None]
    phytonutrients: dict[str, Any]
    source: dict[str, Any]


def _pick_first(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _sanitize_query(query: str) -> str:
    query = (query or "").strip()
    query = re.sub(r"\s+", " ", query)
    return query


def _slugify(value: str) -> str:
    value = (value or "").strip().lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value


def _fetch_text(url: str, *, timeout_s: float, accept: str) -> str | None:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0 Safari/537.36"
            ),
            "Accept": accept,
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout_s) as response:
            raw = response.read()
            charset = getattr(response.headers, "get_content_charset", lambda: None)()
    except Exception:
        return None
    try:
        return raw.decode(charset or "utf-8", errors="replace")
    except Exception:
        return raw.decode("utf-8", errors="replace")


# ---- IndianCalorie provider -------------------------------------------------


def _html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?>.*?</\\1>", "", html)
    html = re.sub(r"(?i)<br\\s*/?>", "\n", html)
    html = re.sub(
        r"(?i)</(p|div|section|article|header|footer|li|tr|h1|h2|h3|h4|h5|h6)>",
        "\n",
        html,
    )
    html = re.sub(r"(?i)</(td|th)>", "\t", html)
    html = re.sub(r"(?s)<[^>]+>", "", html)
    text = html_lib.unescape(html)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text


def _parse_nutrition_facts_lines(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    start_idx = None
    for idx, line in enumerate(lines):
        if "nutrition facts" in line.lower():
            start_idx = idx + 1
            break
    if start_idx is None:
        return []
    facts: list[str] = []
    for line in lines[start_idx:]:
        lowered = line.lower()
        if lowered.startswith("tags") or lowered.startswith("fasting compatibility") or lowered.startswith("similar foods"):
            break
        facts.append(line)
    return facts


def _parse_value_unit(raw: str) -> tuple[float | None, str | None]:
    raw = (raw or "").strip()
    if not raw:
        return None, None
    raw = raw.replace("Âµg", "µg").replace("μg", "µg")
    raw = re.sub(r"\s*\|\s*", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    match = re.match(
        r"^(?P<value>-?\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-zµ]+)?$",
        raw,
    )
    if not match:
        return None, None
    value = _as_float(match.group("value"))
    unit = (match.group("unit") or "").strip() or None
    return value, unit


def _parse_nutrient_line(line: str) -> tuple[str | None, float | None, str | None]:
    line = (line or "").strip()
    if not line:
        return None, None, None
    line = line.replace("Âµg", "µg").replace("μg", "µg")
    line = re.sub(r"\s*\|\s*", " ", line)
    line = re.sub(r"\s+", " ", line).strip()
    if line.lower().startswith("nutrient") and "per 100" in line.lower():
        return None, None, None
    if " per 100" in line.lower():
        return None, None, None

    if "\t" in line:
        parts = [p.strip() for p in line.split("\t") if p.strip()]
        if len(parts) >= 2:
            name = parts[0]
            value, unit = _parse_value_unit(parts[1])
            return name, value, unit

    match = re.match(
        r"^(?P<name>.*?)(?P<value>-?\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-zµ]+)?$",
        line,
    )
    if not match:
        return None, None, None
    name = (match.group("name") or "").strip()
    value = _as_float(match.group("value"))
    unit = (match.group("unit") or "").strip() or None
    if not name:
        return None, None, None
    return name, value, unit


def _iu_to_mcg(value: float, *, kind: str) -> float | None:
    if value < 0:
        return None
    if kind == "vitamin_a":
        # Approx: 1 IU retinol ~= 0.3 µg.
        return value * 0.3
    if kind == "vitamin_d":
        # 1 IU vitamin D ~= 0.025 µg.
        return value * 0.025
    return None


def fetch_indiancalorie_nutrition(query: str, *, timeout_s: float = 8.0) -> NutritionFetchResult | None:
    slug = _slugify(query)
    if not slug:
        return None

    candidates = [
        # India foods
        f"https://www.indiancalorie.com/india/foods/all/{slug}",
        f"https://www.indiancalorie.com/india/foods/breakfast/{slug}",
        f"https://www.indiancalorie.com/india/foods/snacks/{slug}",
        f"https://www.indiancalorie.com/india/foods/lunch/{slug}",
        f"https://www.indiancalorie.com/india/foods/dinner/{slug}",
        f"https://www.indiancalorie.com/india/foods/curry/{slug}",
        f"https://www.indiancalorie.com/india/foods/curries/{slug}",
        f"https://www.indiancalorie.com/india/foods/dal/{slug}",
        f"https://www.indiancalorie.com/india/foods/dal-and-lentils/{slug}",
        # Global foods (some pages live under /global/foods/all)
        f"https://www.indiancalorie.com/global/foods/all/{slug}",
    ]

    for url in candidates:
        html = _fetch_text(url, timeout_s=timeout_s, accept="text/html,*/*")
        if not html:
            continue
        text = _html_to_text(html)
        lines = _parse_nutrition_facts_lines(text)
        if not lines:
            continue

        facts: dict[str, tuple[float, str | None]] = {}
        for line in lines:
            name, value, unit = _parse_nutrient_line(line)
            if name is None or value is None:
                continue
            facts[name.strip().lower()] = (float(value), unit)

        energy_value, energy_unit = facts.get("energy", (None, None))
        if energy_value is None:
            continue
        if energy_unit and energy_unit.lower() in {"kj", "kilojoule", "kilojoules"}:
            energy_value = energy_value / 4.184
            energy_unit = "kcal"
        if energy_unit and energy_unit.lower() != "kcal":
            continue

        def g(name: str) -> float | None:
            value, unit = facts.get(name, (None, None))
            if value is None:
                return None
            if unit and unit.lower() != "g":
                return None
            return float(value)

        def mg(name: str) -> float | None:
            value, unit = facts.get(name, (None, None))
            if value is None or unit is None:
                return None
            converted = _to_mg(float(value), unit)
            return None if converted is None else float(converted)

        def mcg(name: str) -> float | None:
            value, unit = facts.get(name, (None, None))
            if value is None or unit is None:
                return None
            converted = _to_mcg(float(value), unit)
            return None if converted is None else float(converted)

        macros = {
            "protein_g": g("protein"),
            "carbs_g": g("carbohydrates"),
            "fat_g": g("total fat") or g("fat"),
            "fiber_g": g("fiber") or g("dietary fiber"),
            "sugar_g": g("sugars") or g("sugar"),
        }

        vitamins: dict[str, float | None] = {
            "vitamin_a_mcg": None,
            "vitamin_c_mg": mg("vitamin c"),
            "vitamin_d_mcg": None,
            "vitamin_e_mg": mg("vitamin e"),
            "vitamin_k_mcg": mcg("vitamin k"),
            "thiamin_b1_mg": mg("vitamin b1 (thiamine)"),
            "riboflavin_b2_mg": mg("vitamin b2 (riboflavin)"),
            "niacin_b3_mg": mg("vitamin b3 (niacin)"),
            "vitamin_b6_mg": mg("vitamin b6"),
            "folate_mcg": mcg("folate"),
            "vitamin_b12_mcg": mcg("vitamin b12"),
        }

        vitamin_a_val, vitamin_a_unit = facts.get("vitamin a", (None, None))
        if vitamin_a_val is not None and vitamin_a_unit and vitamin_a_unit.lower() == "iu":
            vitamins["vitamin_a_mcg"] = _iu_to_mcg(float(vitamin_a_val), kind="vitamin_a")
        else:
            vitamins["vitamin_a_mcg"] = mcg("vitamin a")

        vitamin_d_val, vitamin_d_unit = facts.get("vitamin d", (None, None))
        if vitamin_d_val is not None and vitamin_d_unit and vitamin_d_unit.lower() == "iu":
            vitamins["vitamin_d_mcg"] = _iu_to_mcg(float(vitamin_d_val), kind="vitamin_d")
        else:
            vitamins["vitamin_d_mcg"] = mcg("vitamin d")

        minerals = {
            "calcium_mg": mg("calcium"),
            "iron_mg": mg("iron"),
            "magnesium_mg": mg("magnesium"),
            "phosphorus_mg": mg("phosphorus"),
            "potassium_mg": mg("potassium"),
            "sodium_mg": mg("sodium"),
            "zinc_mg": mg("zinc"),
        }

        source = {
            "provider": "IndianCalorie",
            "url": url,
            "fetched_at": _utc_now_iso(),
            "unit_conversions": {"vitamin_a_iu_to_mcg": 0.3, "vitamin_d_iu_to_mcg": 0.025},
        }

        return NutritionFetchResult(
            calories_kcal=float(energy_value),
            energy_basis="100g",
            macros=macros,
            vitamins=vitamins,
            minerals=minerals,
            phytonutrients={"note": "Phytonutrients are not listed in this source's nutrition table."},
            source=source,
        )

    return None


# ---- OpenFoodFacts provider -------------------------------------------------


def _openfoodfacts_search(query: str, *, timeout_s: float = 8.0, page_size: int = 8) -> dict[str, Any]:
    params = {
        "search_terms": query,
        "search_simple": "1",
        "action": "process",
        "json": "1",
        "page_size": str(page_size),
    }
    url = "https://world.openfoodfacts.org/cgi/search.pl?" + urlencode(params)
    request = Request(
        url,
        headers={
            "User-Agent": "FoodCaloriesCounter/1.0 (nutrition lookup; +https://openfoodfacts.org)",
            "Accept": "application/json",
        },
        method="GET",
    )
    with urlopen(request, timeout=timeout_s) as response:
        payload = response.read().decode("utf-8", errors="replace")
    return json.loads(payload)


def _score_product(query: str, product: dict[str, Any]) -> int:
    query_l = query.lower().strip()
    product_name = (product.get("product_name") or "").strip().lower()
    generic_name = (product.get("generic_name") or "").strip().lower()
    brand = (product.get("brands") or "").strip().lower()
    nutriments = product.get("nutriments") or {}
    score = 0
    if product_name == query_l:
        score += 50
    if generic_name == query_l:
        score += 35
    if query_l and query_l in product_name:
        score += 15
    if query_l and query_l in generic_name:
        score += 10
    if nutriments:
        score += 10
    if _pick_first(nutriments.get("energy-kcal_serving"), nutriments.get("energy-kcal_100g")) is not None:
        score += 10
    if brand:
        score += 2
    return score


def _extract_openfoodfacts_nutriments(product: dict[str, Any]) -> NutritionFetchResult | None:
    nutriments: dict[str, Any] = product.get("nutriments") or {}
    if not nutriments:
        return None

    def energy_kcal(basis: str) -> float | None:
        if basis not in {"serving", "100g"}:
            return None

        kcal = _as_float(nutriments.get(f"energy-kcal_{basis}"))
        if kcal is not None:
            return kcal

        kj = _as_float(nutriments.get(f"energy-kj_{basis}"))
        if kj is not None:
            return kj / 4.184

        raw = _as_float(nutriments.get(f"energy_{basis}"))
        if raw is None:
            return None
        unit = str(
            _pick_first(nutriments.get("energy_unit"), nutriments.get("energy-kj_unit"), nutriments.get("energy-kcal_unit"))
            or ""
        )
        unit_l = unit.strip().lower()
        if unit_l in {"kcal"}:
            return raw
        if unit_l in {"kj"}:
            return raw / 4.184
        return None

    kcal_serving = energy_kcal("serving")
    kcal_100g = energy_kcal("100g")
    calories_kcal = _pick_first(kcal_serving, kcal_100g)
    energy_basis = "serving" if kcal_serving is not None else ("100g" if kcal_100g is not None else None)

    def gram_key(base: str) -> float | None:
        return _as_float(_pick_first(nutriments.get(f"{base}_serving"), nutriments.get(f"{base}_100g")))

    macros = {
        "protein_g": gram_key("proteins"),
        "carbs_g": gram_key("carbohydrates"),
        "fat_g": gram_key("fat"),
        "fiber_g": gram_key("fiber"),
        "sugar_g": gram_key("sugars"),
    }

    energy_estimated = False
    if calories_kcal is None:
        macros_basis = "serving" if _pick_first(nutriments.get("proteins_serving"), nutriments.get("carbohydrates_serving"), nutriments.get("fat_serving")) is not None else "100g"
        protein = _as_float(nutriments.get(f"proteins_{macros_basis}"))
        carbs = _as_float(nutriments.get(f"carbohydrates_{macros_basis}"))
        fat = _as_float(nutriments.get(f"fat_{macros_basis}"))
        if protein is not None or carbs is not None or fat is not None:
            calories_kcal = max(0.0, 4.0 * float(protein or 0.0) + 4.0 * float(carbs or 0.0) + 9.0 * float(fat or 0.0))
            energy_basis = macros_basis
            energy_estimated = True

    def mg_key(base: str) -> float | None:
        value = _pick_first(nutriments.get(f"{base}_serving"), nutriments.get(f"{base}_100g"))
        unit = _pick_first(nutriments.get(f"{base}_unit"), nutriments.get(f"{base}_unit"))
        numeric = _as_float(value)
        if numeric is None:
            return None
        converted = _to_mg(numeric, str(unit or ""))
        return converted

    def mcg_key(base: str) -> float | None:
        value = _pick_first(nutriments.get(f"{base}_serving"), nutriments.get(f"{base}_100g"))
        unit = _pick_first(nutriments.get(f"{base}_unit"), nutriments.get(f"{base}_unit"))
        numeric = _as_float(value)
        if numeric is None:
            return None
        converted = _to_mcg(numeric, str(unit or ""))
        return converted

    vitamins = {
        "vitamin_a_mcg": mcg_key("vitamin-a"),
        "vitamin_c_mg": mg_key("vitamin-c"),
        "vitamin_d_mcg": mcg_key("vitamin-d"),
        "vitamin_e_mg": mg_key("vitamin-e"),
        "vitamin_k_mcg": mcg_key("vitamin-k"),
        "thiamin_b1_mg": mg_key("vitamin-b1"),
        "riboflavin_b2_mg": mg_key("vitamin-b2"),
        "niacin_b3_mg": mg_key("vitamin-pp"),
        "vitamin_b6_mg": mg_key("vitamin-b6"),
        "folate_mcg": mcg_key("folates"),
        "vitamin_b12_mcg": mcg_key("vitamin-b12"),
    }

    minerals = {
        "calcium_mg": mg_key("calcium"),
        "iron_mg": mg_key("iron"),
        "magnesium_mg": mg_key("magnesium"),
        "phosphorus_mg": mg_key("phosphorus"),
        "potassium_mg": mg_key("potassium"),
        "sodium_mg": mg_key("sodium"),
        "zinc_mg": mg_key("zinc"),
    }

    source = {
        "provider": "OpenFoodFacts",
        "product_name": _pick_first(product.get("product_name"), product.get("generic_name")),
        "brands": product.get("brands"),
        "code": product.get("code"),
        "url": product.get("url"),
        "energy_estimated": energy_estimated,
        "fetched_at": _utc_now_iso(),
    }

    return NutritionFetchResult(
        calories_kcal=calories_kcal,
        energy_basis=energy_basis,
        macros=macros,
        vitamins=vitamins,
        minerals=minerals,
        phytonutrients={"note": "Phytonutrients are not consistently available from this source."},
        source=source,
    )


# ---- Unified fetch ----------------------------------------------------------


REQUIRED_MACRO_KEYS = ("protein_g", "carbs_g", "fat_g", "fiber_g")


def _macro_score(macros: dict[str, float | None] | None) -> int:
    if not macros:
        return 0
    return sum(1 for key in REQUIRED_MACRO_KEYS if macros.get(key) is not None)


def _fill_missing_macros_from_energy(
    macros: dict[str, float | None], *, calories_kcal: float | None
) -> tuple[dict[str, float | None], bool]:
    """
    Best-effort to ensure core macros are present when a provider only exposes energy.
    Uses the available energy (kcal) for the same basis (100g/serving) and assigns any
    remaining kcal to missing macros using a simple default split.
    """
    if calories_kcal is None or not math.isfinite(float(calories_kcal)) or float(calories_kcal) <= 0:
        return macros, False

    updated = dict(macros or {})
    protein = _as_float(updated.get("protein_g")) or 0.0
    carbs = _as_float(updated.get("carbs_g")) or 0.0
    fat = _as_float(updated.get("fat_g")) or 0.0

    kcal_known = (protein * 4.0) + (carbs * 4.0) + (fat * 9.0)
    kcal_remaining = max(float(calories_kcal) - kcal_known, 0.0)

    missing = [key for key in ("protein_g", "carbs_g", "fat_g") if updated.get(key) is None]
    if missing:
        # Default split (kcal share): P 15% | C 55% | F 30%.
        ratios = {"protein_g": 0.15, "carbs_g": 0.55, "fat_g": 0.30}
        if len(missing) == 1:
            key = missing[0]
            divisor = 9.0 if key == "fat_g" else 4.0
            updated[key] = _round(kcal_remaining / divisor, 2)
        else:
            ratio_total = sum(ratios.get(key, 0.0) for key in missing) or float(len(missing))
            for key in missing:
                share = ratios.get(key, 1.0) / ratio_total
                kcal_for_key = kcal_remaining * share
                divisor = 9.0 if key == "fat_g" else 4.0
                updated[key] = _round(kcal_for_key / divisor, 2)

    if updated.get("fiber_g") is None:
        updated["fiber_g"] = 0.0

    changed = any(updated.get(key) != macros.get(key) for key in set(updated) | set(macros))
    return updated, changed


def fetch_food_nutrition(query: str, *, timeout_s: float = 8.0) -> NutritionFetchResult | None:
    query = _sanitize_query(query)
    if not query:
        return None

    best: NutritionFetchResult | None = fetch_indiancalorie_nutrition(query, timeout_s=timeout_s)
    best_score = _macro_score(best.macros) if best else -1

    data = None
    if best is None or best_score < len(REQUIRED_MACRO_KEYS):
        try:
            data = _openfoodfacts_search(query, timeout_s=timeout_s)
        except Exception:
            data = None

    if data is not None:
        products = data.get("products") or []
    else:
        products = []

    if isinstance(products, list) and products:
        scored = sorted(products, key=lambda p: _score_product(query, p), reverse=True)
        off_best: NutritionFetchResult | None = None
        off_best_score = -1
        for product in scored:
            extracted = _extract_openfoodfacts_nutriments(product)
            if extracted is None:
                continue
            score = _macro_score(extracted.macros)
            if score > off_best_score:
                off_best = extracted
                off_best_score = score
            if score >= len(REQUIRED_MACRO_KEYS):
                break

        if off_best is not None and off_best_score > best_score:
            best = off_best
            best_score = off_best_score

    if best is None:
        return None

    if _macro_score(best.macros) < len(REQUIRED_MACRO_KEYS):
        filled, changed = _fill_missing_macros_from_energy(best.macros, calories_kcal=best.calories_kcal)
        if changed:
            source = dict(best.source or {})
            source["macros_estimated"] = True
            source["macros_estimated_note"] = "Filled missing macros from energy using a default macro split."
            best = NutritionFetchResult(
                calories_kcal=best.calories_kcal,
                energy_basis=best.energy_basis,
                macros=filled,
                vitamins=best.vitamins,
                minerals=best.minerals,
                phytonutrients=best.phytonutrients,
                source=source,
            )

    return best


def normalize_to_calories_per_unit(fetched: NutritionFetchResult, *, calories_per_unit: float) -> dict[str, Any] | None:
    """
    Returns a per-UNIT nutrient profile aligned to calories_per_unit.
    - If the fetched profile already has per-serving kcal, uses those per-serving values as-is.
    - If the fetched profile only has per-100g values, scales nutrients linearly based on kcal ratio.
    """
    if calories_per_unit <= 0:
        return None

    factor: float | None = None
    basis_note = None

    if fetched.energy_basis == "serving" and fetched.calories_kcal and fetched.calories_kcal > 0:
        factor = calories_per_unit / fetched.calories_kcal
        basis_note = "Scaled from source serving to match your calories-per-unit."
    elif fetched.energy_basis == "100g" and fetched.calories_kcal and fetched.calories_kcal > 0:
        factor = calories_per_unit / fetched.calories_kcal
        basis_note = "Estimated unit nutrients by scaling from 100g using calories."

    if factor is None or not math.isfinite(factor) or factor <= 0:
        return None

    def scale_map(values: dict[str, float | None], digits: int = 2) -> dict[str, float | None]:
        scaled: dict[str, float | None] = {}
        for key, value in values.items():
            if value is None:
                scaled[key] = None
            else:
                scaled[key] = _round(float(value) * factor, digits=digits)
        return scaled

    return {
        "basis": {"unit": "unit", "note": basis_note},
        "macros": scale_map(fetched.macros, digits=2),
        "vitamins": scale_map(fetched.vitamins, digits=1),
        "minerals": scale_map(fetched.minerals, digits=1),
        "phytonutrients": fetched.phytonutrients,
        "source": fetched.source,
    }


def summarize_macros(profile: dict[str, Any] | None) -> str | None:
    if not profile:
        return None
    macros = profile.get("macros") or {}
    parts = []
    for label, key in (("P", "protein_g"), ("C", "carbs_g"), ("F", "fat_g"), ("Fi", "fiber_g")):
        value = macros.get(key)
        if value is None:
            continue
        parts.append(f"{label} {value}g")
    return " | ".join(parts) if parts else None
