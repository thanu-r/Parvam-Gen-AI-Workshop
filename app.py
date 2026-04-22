from __future__ import annotations

import json
from datetime import date, datetime
from functools import wraps
from pathlib import Path
from typing import Any

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from nutrition import fetch_food_nutrition, normalize_to_calories_per_unit, summarize_macros


BASE_DIR = Path(__file__).resolve().parent
FOODS_FILE = BASE_DIR / "foods.json"
MEALS_FILE = BASE_DIR / "meals.json"
SETTINGS_FILE = BASE_DIR / "settings.json"
USERS_FILE = BASE_DIR / "user.json"
USERS_COMPAT_FILE = BASE_DIR / "users.json"


app = Flask(__name__)
app.secret_key = "change-this-secret-key"

VITAMIN_FIELDS: list[tuple[str, str, str]] = [
    ("vitamin_a_mcg", "Vitamin A", "mcg"),
    ("vitamin_c_mg", "Vitamin C", "mg"),
    ("vitamin_d_mcg", "Vitamin D", "mcg"),
    ("vitamin_e_mg", "Vitamin E", "mg"),
    ("vitamin_k_mcg", "Vitamin K", "mcg"),
    ("thiamin_b1_mg", "Thiamin (B1)", "mg"),
    ("riboflavin_b2_mg", "Riboflavin (B2)", "mg"),
    ("niacin_b3_mg", "Niacin (B3)", "mg"),
    ("vitamin_b6_mg", "Vitamin B6", "mg"),
    ("folate_mcg", "Folate", "mcg"),
    ("vitamin_b12_mcg", "Vitamin B12", "mcg"),
]

MINERAL_FIELDS: list[tuple[str, str, str]] = [
    ("calcium_mg", "Calcium", "mg"),
    ("iron_mg", "Iron", "mg"),
    ("magnesium_mg", "Magnesium", "mg"),
    ("phosphorus_mg", "Phosphorus", "mg"),
    ("potassium_mg", "Potassium", "mg"),
    ("sodium_mg", "Sodium", "mg"),
    ("zinc_mg", "Zinc", "mg"),
]


def ensure_file(path: Path, default_data: Any) -> None:
    if not path.exists() or path.stat().st_size == 0:
        path.write_text(json.dumps(default_data, indent=2), encoding="utf-8")


def load_json(path: Path, default_data: Any) -> Any:
    ensure_file(path, default_data)
    with path.open("r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return default_data


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def bootstrap_files() -> None:
    ensure_file(
        FOODS_FILE,
        {
            "foods": [
                {"name": "Idli", "calories": 70},
                {"name": "Dosa", "calories": 133},
                {"name": "Banana", "calories": 89},
                {"name": "Rice", "calories": 130},
                {"name": "Sambar", "calories": 85},
                {"name": "Boiled Egg", "calories": 78},
            ]
        },
    )
    ensure_file(MEALS_FILE, {"meals": []})
    ensure_file(
        SETTINGS_FILE,
        {
            "default_daily_goal": 2000,
            "users": {
                "demo": {"daily_goal": 2000}
            },
        },
    )
    ensure_file(
        USERS_FILE,
        {
            "users": [
                {
                    "username": "demo",
                    "password": "demo123",
                    "daily_goal": 2000,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            ]
        },
    )
    ensure_file(USERS_COMPAT_FILE, load_json(USERS_FILE, {"users": []}))


bootstrap_files()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "username" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def get_current_username() -> str:
    return session["username"]


def get_users() -> list[dict[str, Any]]:
    return load_json(USERS_FILE, {"users": []}).get("users", [])


def save_users(users: list[dict[str, Any]]) -> None:
    save_json(USERS_FILE, {"users": users})
    save_json(USERS_COMPAT_FILE, {"users": users})


def get_foods() -> list[dict[str, Any]]:
    return load_json(FOODS_FILE, {"foods": []}).get("foods", [])


def get_meals() -> list[dict[str, Any]]:
    return load_json(MEALS_FILE, {"meals": []}).get("meals", [])


def save_meals(meals: list[dict[str, Any]]) -> None:
    save_json(MEALS_FILE, {"meals": meals})


def get_settings() -> dict[str, Any]:
    return load_json(SETTINGS_FILE, {"default_daily_goal": 2000, "users": {}})


def save_settings(settings: dict[str, Any]) -> None:
    save_json(SETTINGS_FILE, settings)


def get_user(username: str) -> dict[str, Any] | None:
    for user in get_users():
        if user["username"].lower() == username.lower():
            return user
    return None


def password_matches(stored_password: str, entered_password: str) -> bool:
    if stored_password == entered_password:
        return True
    try:
        return check_password_hash(stored_password, entered_password)
    except ValueError:
        return False


def get_daily_goal(username: str) -> int:
    user = get_user(username)
    settings = get_settings()
    if user and user.get("daily_goal"):
        return int(user["daily_goal"])
    user_goal = settings.get("users", {}).get(username, {}).get("daily_goal")
    if user_goal:
        return int(user_goal)
    return int(settings.get("default_daily_goal", 2000))


def set_daily_goal(username: str, goal: int) -> None:
    users = get_users()
    for user in users:
        if user["username"] == username:
            user["daily_goal"] = goal
            break
    save_users(users)

    settings = get_settings()
    settings.setdefault("users", {})
    settings["users"][username] = {"daily_goal": goal}
    save_settings(settings)


def find_food_calories(food_name: str) -> int | None:
    for item in get_foods():
        if item["name"].strip().lower() == food_name.strip().lower():
            return int(item["calories"])
    return None


def find_food(food_name: str) -> dict[str, Any] | None:
    food_name = (food_name or "").strip().lower()
    if not food_name:
        return None
    for item in get_foods():
        if (item.get("name") or "").strip().lower() == food_name:
            return item
    return None


def upsert_food(food_item: dict[str, Any]) -> None:
    foods = get_foods()
    target_name = (food_item.get("name") or "").strip().lower()
    if not target_name:
        return
    updated = False
    for idx, item in enumerate(foods):
        if (item.get("name") or "").strip().lower() == target_name:
            foods[idx] = {**item, **food_item}
            updated = True
            break
    if not updated:
        foods.append(food_item)
    save_json(FOODS_FILE, {"foods": foods})


REQUIRED_MACRO_KEYS = ("protein_g", "carbs_g", "fat_g", "fiber_g")


def nutrients_have_required_macros(nutrients: dict[str, Any] | None) -> bool:
    if not nutrients:
        return False
    macros = nutrients.get("macros") or {}
    return all(macros.get(key) is not None for key in REQUIRED_MACRO_KEYS)


def estimate_unit_nutrients_from_calories(calories_per_unit: float) -> dict[str, Any]:
    calories = max(float(calories_per_unit), 0.0)
    protein_g = round((calories * 0.15) / 4.0, 2)
    carbs_g = round((calories * 0.55) / 4.0, 2)
    fat_g = round((calories * 0.30) / 9.0, 2)

    return {
        "basis": {"unit": "unit", "note": "Estimated macros from calories (no online data found)."},
        "macros": {
            "protein_g": protein_g,
            "carbs_g": carbs_g,
            "fat_g": fat_g,
            "fiber_g": 0.0,
            "sugar_g": None,
        },
        "vitamins": {},
        "minerals": {},
        "phytonutrients": {},
        "source": {
            "provider": "Estimated",
            "fetched_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        },
    }


def get_food_details(
    food_name: str,
    *,
    fetch_if_missing: bool = False,
    calories_hint: int | None = None,
) -> dict[str, Any] | None:
    local = find_food(food_name)
    if local and local.get("calories") is not None:
        calories = int(local["calories"])
        nutrients = local.get("nutrients")
        if nutrients and (not fetch_if_missing or nutrients_have_required_macros(nutrients)):
            return {
                "name": local.get("name") or food_name,
                "calories": calories,
                "nutrients": nutrients,
                "macros_summary": summarize_macros(nutrients),
                "source": (nutrients or {}).get("source"),
                "cached": True,
            }
        if not fetch_if_missing:
            return {
                "name": local.get("name") or food_name,
                "calories": calories,
                "nutrients": None,
                "macros_summary": None,
                "source": None,
                "cached": True,
            }

    if not fetch_if_missing:
        return None

    calories_for_unit = calories_hint
    if calories_for_unit is None and local and local.get("calories") is not None:
        calories_for_unit = int(local["calories"])

    fetched = fetch_food_nutrition(food_name, timeout_s=6.0)
    if fetched is None and calories_for_unit is None:
        return None

    if fetched is not None:
        if calories_for_unit is None and fetched.calories_kcal is not None:
            calories_for_unit = int(round(float(fetched.calories_kcal)))

    if calories_for_unit is None:
        return None

    if fetched is not None:
        normalized = normalize_to_calories_per_unit(fetched, calories_per_unit=float(calories_for_unit))
    else:
        normalized = estimate_unit_nutrients_from_calories(float(calories_for_unit))

    if normalized is None:
        normalized = estimate_unit_nutrients_from_calories(float(calories_for_unit))

    updated_food: dict[str, Any] = {
        "name": (local.get("name") if local else None) or food_name.strip(),
        "calories": int(calories_for_unit),
        "nutrients": normalized,
        "nutrients_updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    upsert_food(updated_food)
    return {
        "name": updated_food["name"],
        "calories": int(updated_food["calories"]),
        "nutrients": normalized,
        "macros_summary": summarize_macros(normalized),
        "source": (normalized or {}).get("source"),
        "cached": False,
    }


def scale_nutrients(nutrients: dict[str, Any] | None, factor: float) -> dict[str, Any] | None:
    if not nutrients or factor <= 0:
        return None

    def scale_map(values: dict[str, Any], digits: int = 2) -> dict[str, Any]:
        scaled: dict[str, Any] = {}
        for key, value in (values or {}).items():
            if value is None:
                scaled[key] = None
            else:
                try:
                    scaled[key] = round(float(value) * factor, digits)
                except (TypeError, ValueError):
                    scaled[key] = value
        return scaled

    return {
        "basis": {"unit": "meal", "note": f"Total for qty x{factor:g}."},
        "macros": scale_map(nutrients.get("macros") or {}, digits=2),
        "vitamins": scale_map(nutrients.get("vitamins") or {}, digits=1),
        "minerals": scale_map(nutrients.get("minerals") or {}, digits=1),
        "phytonutrients": nutrients.get("phytonutrients") or {},
        "source": nutrients.get("source") or {},
    }


def enrich_meals_with_nutrients(meals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for meal in meals:
        item = dict(meal)
        calories_per_unit = item.get("calories_per_unit")
        if calories_per_unit is None:
            try:
                qty = int(item.get("qty", 1) or 1)
                total_calories = int(item.get("calories", 0) or 0)
                calories_per_unit = int(round(total_calories / max(qty, 1)))
            except (TypeError, ValueError, ZeroDivisionError):
                calories_per_unit = None
        qty = int(item.get("qty", 1) or 1)

        per_unit_nutrients = item.get("nutrients_per_unit")
        provider = (((per_unit_nutrients or {}).get("source") or {}).get("provider") or "").strip().lower()
        should_refresh = (not nutrients_have_required_macros(per_unit_nutrients)) or provider == "estimated"
        if should_refresh:
            food = find_food(item.get("food", ""))
            cached = (food or {}).get("nutrients")
            if nutrients_have_required_macros(cached):
                per_unit_nutrients = cached
            else:
                if calories_per_unit is not None:
                    per_unit_nutrients = estimate_unit_nutrients_from_calories(float(calories_per_unit))
                    item["nutrients_source"] = (per_unit_nutrients or {}).get("source")

        item["nutrients_per_unit"] = per_unit_nutrients
        item["nutrients_total"] = scale_nutrients(per_unit_nutrients, float(max(qty, 1)))
        item["macros_summary"] = summarize_macros(item["nutrients_total"]) or summarize_macros(per_unit_nutrients)
        enriched.append(item)
    return enriched


def sum_nutrients(profiles: list[dict[str, Any] | None]) -> dict[str, Any] | None:
    def add_maps(target: dict[str, float], values: dict[str, Any] | None) -> None:
        for key, value in (values or {}).items():
            if value is None:
                continue
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            target[key] = target.get(key, 0.0) + number

    totals: dict[str, float] = {}
    vitamin_totals: dict[str, float] = {}
    mineral_totals: dict[str, float] = {}

    any_found = False
    for profile in profiles:
        if not profile:
            continue
        any_found = True
        add_maps(totals, (profile.get("macros") or {}))
        add_maps(vitamin_totals, (profile.get("vitamins") or {}))
        add_maps(mineral_totals, (profile.get("minerals") or {}))

    if not any_found:
        return None
    return {"macros": totals, "vitamins": vitamin_totals, "minerals": mineral_totals}


def get_daily_nutrient_totals(username: str, selected_date: str) -> dict[str, Any] | None:
    meals_today = enrich_meals_with_nutrients(get_todays_meals(username, selected_date))
    profiles = [meal.get("nutrients_total") for meal in meals_today]
    summed = sum_nutrients(profiles)
    if not summed:
        return None
    return {
        "macros": {
            "protein_g": round(float(summed["macros"].get("protein_g", 0.0)), 2),
            "carbs_g": round(float(summed["macros"].get("carbs_g", 0.0)), 2),
            "fat_g": round(float(summed["macros"].get("fat_g", 0.0)), 2),
            "fiber_g": round(float(summed["macros"].get("fiber_g", 0.0)), 2),
        },
        "vitamins": {key: round(float(value), 1) for key, value in (summed.get("vitamins") or {}).items()},
        "minerals": {key: round(float(value), 1) for key, value in (summed.get("minerals") or {}).items()},
    }

def get_todays_meals(username: str, selected_date: str) -> list[dict[str, Any]]:
    return [
        meal
        for meal in get_meals()
        if meal.get("username") == username and meal.get("date") == selected_date
    ]


def calculate_daily_total(username: str, selected_date: str) -> int:
    return sum(int(meal.get("calories", 0)) for meal in get_todays_meals(username, selected_date))


def progress_details(total: int, goal: int) -> dict[str, Any]:
    goal = max(goal, 1)
    percentage = min(round((total / goal) * 100, 2), 100)
    exceeded = total > goal
    return {
        "total": total,
        "goal": goal,
        "remaining": goal - total,
        "percentage": percentage,
        "exceeded": exceeded,
    }


@app.context_processor
def inject_today() -> dict[str, str]:
    return {"today_string": date.today().isoformat()}


@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("home"))
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_user(username)

        if user and password_matches(user["password"], password):
            session["username"] = user["username"]
            flash("Welcome back.", "success")
            return redirect(url_for("home"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        daily_goal = int(request.form.get("daily_goal", 2000) or 2000)

        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template("registier.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("registier.html")

        if get_user(username):
            flash("Username already exists.", "warning")
            return render_template("registier.html")

        users = get_users()
        users.append(
            {
                "username": username,
                "password": generate_password_hash(password),
                "daily_goal": daily_goal,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        save_users(users)
        set_daily_goal(username, daily_goal)
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("registier.html")


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/home")
@login_required
def home():
    username = get_current_username()
    selected_date = date.today().isoformat()
    daily_goal = get_daily_goal(username)
    summary = progress_details(calculate_daily_total(username, selected_date), daily_goal)
    recent_meals = sorted(get_todays_meals(username, selected_date), key=lambda item: item["id"], reverse=True)[:5]
    recent_meals = enrich_meals_with_nutrients(recent_meals)
    return render_template(
        "home.html",
        username=username,
        selected_date=selected_date,
        summary=summary,
        recent_meals=recent_meals,
    )


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    username = get_current_username()
    selected_date = request.args.get("date") or date.today().isoformat()

    if request.method == "POST":
        food_name = request.form.get("food", "").strip()
        meal_type = request.form.get("meal", "").strip()
        entry_date = request.form.get("date") or selected_date
        qty = int(request.form.get("qty", 1) or 1)
        manual_calories = request.form.get("calories", "").strip()

        calories_per_unit = find_food_calories(food_name)
        if manual_calories:
            try:
                calories_per_unit = int(manual_calories)
            except ValueError:
                calories_per_unit = None

        if not food_name or not meal_type or calories_per_unit is None:
            flash("Enter a food item, meal type, and valid calories.", "danger")
            return redirect(url_for("dashboard", date=entry_date))

        nutrients_per_unit = None
        nutrients_source = None
        details = get_food_details(
            food_name,
            fetch_if_missing=False,
            calories_hint=int(calories_per_unit),
        )
        if details and details.get("nutrients"):
            nutrients_per_unit = details["nutrients"]
            nutrients_source = details.get("source")
        else:
            nutrients_per_unit = estimate_unit_nutrients_from_calories(float(calories_per_unit))
            nutrients_source = (nutrients_per_unit or {}).get("source")

        total_calories = calories_per_unit * max(qty, 1)
        meals = get_meals()
        next_id = (max((meal.get("id", 0) for meal in meals), default=0)) + 1
        meals.append(
            {
                "id": next_id,
                "username": username,
                "date": entry_date,
                "food": food_name,
                "meal": meal_type,
                "calories": total_calories,
                "qty": qty,
                "calories_per_unit": int(calories_per_unit),
                "nutrients_per_unit": nutrients_per_unit,
                "nutrients_source": nutrients_source,
            }
        )
        save_meals(meals)
        flash(f"{food_name} added to your {meal_type.lower()} log.", "success")
        return redirect(url_for("dashboard", date=entry_date))

    meals_today = get_todays_meals(username, selected_date)
    meals_today = enrich_meals_with_nutrients(meals_today)
    daily_goal = get_daily_goal(username)
    summary = progress_details(calculate_daily_total(username, selected_date), daily_goal)
    nutrient_totals = get_daily_nutrient_totals(username, selected_date)

    return render_template(
        "dashboard.html",
        username=username,
        foods=get_foods(),
        meals=sorted(meals_today, key=lambda item: item["id"], reverse=True),
        selected_date=selected_date,
        summary=summary,
        nutrient_totals=nutrient_totals,
        vitamin_fields=VITAMIN_FIELDS,
        mineral_fields=MINERAL_FIELDS,
    )


@app.route("/history")
@login_required
def history():
    username = get_current_username()
    meals = [meal for meal in get_meals() if meal.get("username") == username]
    meals = sorted(meals, key=lambda item: (item["date"], item["id"]), reverse=True)
    meals = enrich_meals_with_nutrients(meals)

    grouped_meals: dict[str, list[dict[str, Any]]] = {}
    for meal in meals:
        meal_date = meal.get("date", "")
        grouped_meals.setdefault(meal_date, []).append(meal)

    daily_history = [
        {
            "date": meal_date,
            "meals": entries,
            "entries": len(entries),
            "calories": sum(int(entry.get("calories", 0)) for entry in entries),
        }
        for meal_date, entries in grouped_meals.items()
    ]

    total_calories = sum(int(meal.get("calories", 0)) for meal in meals)
    total_entries = len(meals)
    total_days = len(daily_history)
    return render_template(
        "history.html",
        daily_history=daily_history,
        username=username,
        total_calories=total_calories,
        total_entries=total_entries,
        total_days=total_days,
        vitamin_fields=VITAMIN_FIELDS,
        mineral_fields=MINERAL_FIELDS,
    )


@app.route("/edit/<int:meal_id>", methods=["GET", "POST"])
@login_required
def edit_meal(meal_id: int):
    username = get_current_username()
    next_page = request.args.get("next") or request.form.get("next") or "history"
    redirect_target = url_for("dashboard") if next_page == "dashboard" else url_for("history")

    meals = get_meals()
    meal_to_edit = next(
        (meal for meal in meals if meal.get("id") == meal_id and meal.get("username") == username),
        None,
    )

    if meal_to_edit is None:
        flash("Meal entry not found.", "warning")
        return redirect(redirect_target)

    if request.method == "POST":
        food_name = request.form.get("food", "").strip()
        meal_type = request.form.get("meal", "").strip()
        entry_date = request.form.get("date", "").strip()
        manual_calories = request.form.get("calories", "").strip()

        try:
            qty = max(int(request.form.get("qty", 1) or 1), 1)
        except ValueError:
            qty = 0

        calories_per_unit = find_food_calories(food_name)
        if manual_calories:
            try:
                calories_per_unit = int(manual_calories)
            except ValueError:
                calories_per_unit = None

        if not food_name or not meal_type or not entry_date or qty < 1 or calories_per_unit is None:
            flash("Enter valid meal details before saving.", "danger")
            return render_template(
                "edit_meal.html",
                meal=meal_to_edit,
                foods=get_foods(),
                next_page=next_page,
            )

        meal_to_edit["food"] = food_name
        meal_to_edit["meal"] = meal_type
        meal_to_edit["date"] = entry_date
        meal_to_edit["qty"] = qty
        meal_to_edit["calories"] = max(calories_per_unit, 1) * qty
        meal_to_edit["calories_per_unit"] = int(calories_per_unit)

        details = get_food_details(
            food_name,
            fetch_if_missing=False,
            calories_hint=int(calories_per_unit),
        )
        if details and details.get("nutrients"):
            meal_to_edit["nutrients_per_unit"] = details["nutrients"]
            meal_to_edit["nutrients_source"] = details.get("source")
        else:
            estimated = estimate_unit_nutrients_from_calories(float(calories_per_unit))
            meal_to_edit["nutrients_per_unit"] = estimated
            meal_to_edit["nutrients_source"] = (estimated or {}).get("source")

        save_meals(meals)
        flash("Meal updated.", "success")
        return redirect(redirect_target)

    return render_template(
        "edit_meal.html",
        meal=meal_to_edit,
        foods=get_foods(),
        next_page=next_page,
    )


@app.route("/delete/<int:meal_id>", methods=["POST"])
@login_required
def delete_meal(meal_id: int):
    username = get_current_username()
    meals = get_meals()
    remaining = [meal for meal in meals if not (meal.get("id") == meal_id and meal.get("username") == username)]
    save_meals(remaining)
    flash("Meal deleted.", "success")
    return redirect(request.referrer or url_for("history"))


@app.route("/clear-history", methods=["POST"])
@login_required
def clear_history():
    username = get_current_username()
    meals = [meal for meal in get_meals() if meal.get("username") != username]
    save_meals(meals)
    flash("History cleared.", "success")
    return redirect(url_for("history"))


@app.route("/clear-history/<string:date_str>", methods=["POST"])
@login_required
def clear_history_day(date_str: str):
    username = get_current_username()
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        flash("Invalid date for clear history.", "danger")
        return redirect(url_for("history"))

    meals = get_meals()
    remaining = [
        meal
        for meal in meals
        if not (meal.get("username") == username and meal.get("date") == date_str)
    ]
    save_meals(remaining)
    flash(f"History cleared for {date_str}.", "success")
    return redirect(url_for("history"))


@app.route("/update-goal", methods=["POST"])
@login_required
def update_goal():
    username = get_current_username()
    goal = int(request.form.get("daily_goal", 2000) or 2000)
    set_daily_goal(username, max(goal, 1))
    flash("Daily calorie goal updated.", "success")
    return redirect(url_for("dashboard", date=request.form.get("date") or date.today().isoformat()))


@app.route("/api/food-calories")
@login_required
def food_calories():
    food_name = request.args.get("name", "").strip()
    details = get_food_details(food_name, fetch_if_missing=False)
    if not details:
        calories = find_food_calories(food_name)
        if calories is None:
            return jsonify({"found": False, "calories": None})
        return jsonify({"found": True, "calories": calories})
    return jsonify({"found": True, "calories": details.get("calories")})


@app.route("/api/food-details")
@login_required
def food_details():
    food_name = request.args.get("name", "").strip()
    fetch = request.args.get("fetch", "0").strip() == "1"
    calories_hint = request.args.get("calories_hint", "").strip()
    try:
        calories_hint_int = int(calories_hint) if calories_hint else None
    except ValueError:
        calories_hint_int = None

    details = get_food_details(
        food_name,
        fetch_if_missing=fetch,
        calories_hint=calories_hint_int,
    )
    if not details:
        return jsonify({"found": False})
    return jsonify({"found": True, **details})


if __name__ == "__main__":
    app.run(debug=True)
