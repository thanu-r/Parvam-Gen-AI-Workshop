document.addEventListener("DOMContentLoaded", () => {
  const THEME_KEY = "fcc_theme";
  const root = document.documentElement;
  const themeToggle = document.getElementById("theme-toggle");

  const systemPrefersDark = () => {
    if (!window.matchMedia) {
      return false;
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  };

  const readStoredTheme = () => {
    try {
      return localStorage.getItem(THEME_KEY);
    } catch {
      return null;
    }
  };

  const storeTheme = (theme) => {
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch {
      // ignore
    }
  };

  const applyTheme = (theme) => {
    const resolved = theme === "dark" ? "dark" : "light";
    root.dataset.theme = resolved;
    if (themeToggle) {
      themeToggle.setAttribute("aria-pressed", resolved === "dark" ? "true" : "false");
    }
  };

  const storedTheme = readStoredTheme();
  applyTheme(storedTheme || (systemPrefersDark() ? "dark" : "light"));

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const next = root.dataset.theme === "dark" ? "light" : "dark";
      applyTheme(next);
      storeTheme(next);
    });
  }

  if (!storedTheme && window.matchMedia) {
    const query = window.matchMedia("(prefers-color-scheme: dark)");
    if (query.addEventListener) {
      query.addEventListener("change", (event) => applyTheme(event.matches ? "dark" : "light"));
    } else if (query.addListener) {
      query.addListener((event) => applyTheme(event.matches ? "dark" : "light"));
    }
  }

  const dismissFlashes = () => {
    const flashes = document.querySelectorAll(".flash");
    if (!flashes.length) {
      return;
    }
    flashes.forEach((flash) => {
      setTimeout(() => flash.classList.add("dismissed"), 4200);
      setTimeout(() => flash.remove(), 4700);
    });
  };
  dismissFlashes();

  const foodInput = document.getElementById("food-item");
  const caloriesInput = document.getElementById("calories");
  const nutrientPreview = document.getElementById("nutrient-preview");

  const setPreview = (text) => {
    if (!nutrientPreview) {
      return;
    }
    nutrientPreview.textContent = text || "";
  };

  const formatNumber = (value, digits = 2) => {
    if (value === null || value === undefined || value === "") {
      return null;
    }
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      return null;
    }
    return parsed.toFixed(digits).replace(/\.00$/, "");
  };

  const buildNutrientPreview = (nutrients) => {
    if (!nutrients) {
      return "";
    }
    const macros = nutrients.macros || {};
    const vitamins = nutrients.vitamins || {};
    const minerals = nutrients.minerals || {};

    const lines = [];
    const protein = formatNumber(macros.protein_g, 2);
    const carbs = formatNumber(macros.carbs_g, 2);
    const fat = formatNumber(macros.fat_g, 2);
    const fiber = formatNumber(macros.fiber_g, 2);

    if (protein || carbs || fat || fiber) {
      lines.push("Per unit (estimated):");
      if (protein) lines.push(`- Protein: ${protein} g`);
      if (carbs) lines.push(`- Carbohydrates: ${carbs} g`);
      if (fat) lines.push(`- Fats: ${fat} g`);
      if (fiber) lines.push(`- Fiber: ${fiber} g`);
    }

    const vitaminLines = [];
    const v = (label, value, unit, digits = 1) => {
      const formatted = formatNumber(value, digits);
      if (formatted) vitaminLines.push(`- ${label}: ${formatted} ${unit}`);
    };
    v("Vitamin A", vitamins.vitamin_a_mcg, "mcg", 0);
    v("Vitamin C", vitamins.vitamin_c_mg, "mg");
    v("Vitamin D", vitamins.vitamin_d_mcg, "mcg", 1);
    v("Vitamin E", vitamins.vitamin_e_mg, "mg");
    v("Vitamin K", vitamins.vitamin_k_mcg, "mcg", 0);
    v("Thiamin (B1)", vitamins.thiamin_b1_mg, "mg");
    v("Riboflavin (B2)", vitamins.riboflavin_b2_mg, "mg");
    v("Niacin (B3)", vitamins.niacin_b3_mg, "mg");
    v("Vitamin B6", vitamins.vitamin_b6_mg, "mg");
    v("Folate", vitamins.folate_mcg, "mcg", 0);
    v("Vitamin B12", vitamins.vitamin_b12_mcg, "mcg", 1);

    if (vitaminLines.length) {
      lines.push("");
      lines.push("Vitamins:");
      lines.push(...vitaminLines);
    }

    const mineralLines = [];
    const m = (label, value) => {
      const formatted = formatNumber(value, 1);
      if (formatted) mineralLines.push(`- ${label}: ${formatted} mg`);
    };
    m("Calcium", minerals.calcium_mg);
    m("Iron", minerals.iron_mg);
    m("Magnesium", minerals.magnesium_mg);
    m("Phosphorus", minerals.phosphorus_mg);
    m("Potassium", minerals.potassium_mg);
    m("Sodium", minerals.sodium_mg);
    m("Zinc", minerals.zinc_mg);

    if (mineralLines.length) {
      lines.push("");
      lines.push("Minerals:");
      lines.push(...mineralLines);
    }

    return lines.join("\n");
  };

  const lookupFood = async (name, fetchOnline) => {
    const hint = caloriesInput ? caloriesInput.value.trim() : "";
    const params = new URLSearchParams({ name, fetch: fetchOnline ? "1" : "0" });
    if (fetchOnline && hint) {
      params.set("calories_hint", hint);
    }
    const response = await fetch(`/api/food-details?${params.toString()}`);
    return await response.json();
  };

  const fillFoodDetails = async (fetchOnline) => {
    if (!foodInput || !caloriesInput) {
      return;
    }
    const value = foodInput.value.trim();
    if (!value) {
      setPreview("");
      return;
    }

    try {
      const data = await lookupFood(value, fetchOnline);
      if (!data.found) {
        setPreview(fetchOnline ? "No nutrient data found online for this item yet." : "");
        return;
      }
      if (data.calories && !caloriesInput.value) {
        caloriesInput.value = data.calories;
      }
      setPreview(
        buildNutrientPreview(data.nutrients) || (data.macros_summary ? `Macros: ${data.macros_summary}` : "")
      );
    } catch (error) {
      console.error("Unable to fetch food details", error);
      setPreview("");
    }
  };

  let debounce = null;
  const debouncedLookup = () => {
    if (!foodInput) {
      return;
    }
    if (debounce) {
      clearTimeout(debounce);
    }
    debounce = setTimeout(() => fillFoodDetails(false), 350);
  };

  if (foodInput && caloriesInput) {
    foodInput.addEventListener("input", debouncedLookup);
    foodInput.addEventListener("change", () => fillFoodDetails(true));
    foodInput.addEventListener("blur", () => fillFoodDetails(true));
  }

  const historySearch = document.getElementById("history-search");
  if (historySearch) {
    const items = Array.from(document.querySelectorAll(".meal-item[data-search]"));
    const normalize = (value) => (value || "").toString().trim().toLowerCase();

    historySearch.addEventListener("input", () => {
      const query = normalize(historySearch.value);
      items.forEach((item) => {
        const haystack = normalize(item.getAttribute("data-search"));
        item.style.display = !query || haystack.includes(query) ? "" : "none";
      });
    });
  }
});
