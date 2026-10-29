
import os
import re
import csv
import io
import json
import sqlite3
import time
from pathlib import Path
from datetime import date, timedelta

import streamlit as st
from google import genai
from google.genai import types


# -------------------- APP SETTINGS --------------------

st.set_page_config(
    page_title="SmartChef AI",
    page_icon="🍲",
    layout="wide",
)

# -------------------- PROFESSIONAL VISUAL THEME --------------------

st.markdown("""
<style>
/* Overall page */
.stApp {
    background: #f7f8f5;
    color: #25332d;
    font-family: "Segoe UI", sans-serif;
}

[data-testid="stAppViewContainer"] > .main {
    background: #f7f8f5;
}

.block-container {
    max-width: 1250px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

/* Main heading */
h1 {
    color: #183c30 !important;
    font-weight: 800 !important;
    letter-spacing: -1.2px;
}

h2, h3 {
    color: #244b3a !important;
    font-weight: 700 !important;
    letter-spacing: -0.3px;
}

p, label, .stMarkdown {
    line-height: 1.65;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #e8f1e8 0%, #f3f5ed 100%);
    border-right: 1px solid #dce6db;
}

[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #214a36 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 1px solid #dce5dc;
}

.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 10px 10px 0 0;
    padding: 12px 17px;
    color: #52635a;
    font-weight: 600;
}

.stTabs [data-baseweb="tab"]:hover {
    background: #eaf1e9;
    color: #214a36;
}

.stTabs [aria-selected="true"] {
    color: #1f6b4a !important;
    border-bottom-color: #2e8b57 !important;
}

/* Buttons */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
    border-radius: 10px;
    min-height: 44px;
    font-weight: 650;
    border: 1px solid #d6e2d6;
    transition: all 0.18s ease;
}

.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {
    background: linear-gradient(135deg, #26764e, #1d5e3e);
    color: white;
    border: none;
    box-shadow: 0 3px 8px rgba(31, 94, 62, 0.14);
}

.stButton > button:hover,
.stDownloadButton > button:hover,
.stFormSubmitButton > button:hover {
    border-color: #38865d;
    color: #1d5e3e;
    transform: translateY(-1px);
}

.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover {
    color: white;
    background: #194f35;
}

/* Inputs and dropdowns */
div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
div[data-baseweb="textarea"] > div {
    border-radius: 10px;
    border-color: #d7e1d7;
    background: #ffffff;
}

div[data-baseweb="input"] > div:focus-within,
div[data-baseweb="select"] > div:focus-within,
div[data-baseweb="textarea"] > div:focus-within {
    border-color: #38865d;
    box-shadow: 0 0 0 1px #38865d;
}

[data-testid="stNumberInput"] button {
    border-radius: 8px;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e1e9df;
    border-radius: 16px;
    padding: 18px 20px;
    box-shadow: 0 4px 14px rgba(36, 75, 58, 0.045);
}

[data-testid="stMetricLabel"] {
    color: #617267;
    font-weight: 600;
}

[data-testid="stMetricValue"] {
    color: #245c40;
    font-weight: 800;
}

/* Forms and expanders */
[data-testid="stForm"],
[data-testid="stExpander"] {
    border: 1px solid #e0e8de;
    border-radius: 14px;
    background: #ffffff;
}

[data-testid="stExpander"] summary {
    font-weight: 650;
    color: #244b3a;
}

/* Notices */
[data-testid="stAlert"] {
    border-radius: 12px;
    border: 1px solid #e0e8de;
}

/* Dividers and footer */
hr {
    border-color: #dfe7dd !important;
}

[data-testid="stCaptionContainer"] {
    color: #738076;
}

/* Download buttons */
.stDownloadButton > button {
    background: #edf5ed;
    color: #245c40;
}

/* Keep mobile layouts readable */
@media (max-width: 768px) {
    .block-container {
        padding: 1rem 1rem 2rem;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 9px 10px;
        font-size: 0.85rem;
    }

    h1 {
        font-size: 2rem !important;
    }
}
</style>
""", unsafe_allow_html=True)

# -------------------- END PROFESSIONAL VISUAL THEME --------------------

DB_PATH = Path(__file__).with_name("smartchef.db")


# -------------------- DATABASE --------------------

def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit TEXT NOT NULL,
                expiry_date TEXT,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS waste_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit TEXT NOT NULL,
                action TEXT NOT NULL CHECK(action IN ('Rescued', 'Wasted')),
                reason TEXT DEFAULT '',
                logged_date TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


def get_pantry():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM ingredients
            ORDER BY
                CASE WHEN expiry_date IS NULL THEN 1 ELSE 0 END,
                expiry_date ASC,
                name COLLATE NOCASE ASC
        """).fetchall()
        return [dict(row) for row in rows]


def add_ingredient(name, quantity, unit, expiry_date):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO ingredients
                (name, quantity, unit, expiry_date)
            VALUES (?, ?, ?, ?)
        """, (
            name.strip(),
            quantity,
            unit,
            expiry_date.isoformat() if expiry_date else None,
        ))


def delete_ingredient(item_id):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM ingredients WHERE id = ?",
            (item_id,),
        )


def get_favorites():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM favorites
            ORDER BY created_at DESC
        """).fetchall()
        return [dict(row) for row in rows]


def add_favorite(recipe):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO favorites (recipe) VALUES (?)",
            (recipe,),
        )


def delete_favorite(favorite_id):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM favorites WHERE id = ?",
            (favorite_id,),
        )


def log_waste_event(item_name, quantity, unit, action, reason, logged_date):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO waste_log
                (item_name, quantity, unit, action, reason, logged_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            item_name.strip(), quantity, unit, action,
            reason.strip(), logged_date.isoformat(),
        ))


def get_waste_log():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM waste_log
            ORDER BY logged_date DESC, id DESC
        """).fetchall()
        return [dict(row) for row in rows]


def delete_waste_event(event_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM waste_log WHERE id = ?", (event_id,))


def waste_log_csv(rows):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Ingredient", "Quantity", "Unit", "Action", "Notes"])
    for row in rows:
        writer.writerow([
            row["logged_date"], row["item_name"], row["quantity"],
            row["unit"], row["action"], row["reason"],
        ])
    return output.getvalue().encode("utf-8-sig")


initialize_database()


# -------------------- GEMINI API --------------------

def get_api_key():
    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        key = ""

    return key or os.getenv("GEMINI_API_KEY", "")


def generate_recipe(
    ingredients,
    cuisine,
    diet,
    meal_type,
    time_limit,
    servings,
    skill,
    extra_notes,
):
    api_key = get_api_key()

    if not api_key:
        raise ValueError(
            "Gemini API key not found. Check your "
            ".streamlit/secrets.toml configuration."
        )

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are SmartChef AI, a practical cooking assistant for students
and people living alone.

Create one affordable, realistic recipe using these details.

Available ingredients:
{ingredients}

Preferred cuisine: {cuisine}
Dietary preference: {diet}
Meal type: {meal_type}
Maximum total cooking time: {time_limit} minutes
Servings: {servings}
Cooking skill: {skill}
Additional instructions: {extra_notes or 'None'}

Requirements:
1. Give the recipe a clear title and short description.
2. List ingredients with quantities and common kitchen measures.
3. Give numbered, beginner-friendly cooking steps.
4. Include preparation time, cooking time, total time and servings.
5. Prefer ingredients already available to the user.
6. Clearly identify ingredients the user needs to buy.
7. Prefer affordable ingredients, minimal equipment and less washing up.
8. If ingredients marked as needing attention are provided,
   prioritize them where appropriate.
9. Never assume that food is safe merely because it looks or smells
   normal or because an expiry date has not passed.
10. Do not recommend using food that may be unsafe. If a date has
    passed, advise the user to check appropriate food-safety guidance.
11. Suggest practical substitutions where possible.
12. Mention relevant allergens and food-safety precautions.
13. Do not invent precise nutrition figures.
14. Format the answer in readable Markdown with headings.
"""
    # Retry temporary Gemini server errors
    max_attempts = 3

    for attempt in range(max_attempts):
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
            )

            if not response.text:
                raise RuntimeError(
                    "The AI returned an empty response. Please try again."
                )

            return response.text

        except Exception as exc:
            error_text = str(exc).upper()

            temporary_error = any(
                marker in error_text
                for marker in (
                    "503",
                    "UNAVAILABLE",
                    "429",
                    "RESOURCE_EXHAUSTED",
                    "500",
                    "INTERNAL",
                    "502",
                    "504",
                )
            )

            if not temporary_error or attempt == max_attempts - 1:
                raise

            wait_seconds = 2 ** (attempt + 1)
            time.sleep(wait_seconds)

    raise RuntimeError(
        "Gemini is temporarily unavailable. Please try again later."
    )


def detect_ingredients_from_image(image_bytes, mime_type):
    """Use Gemini vision to suggest ingredients visible in an uploaded photo."""
    api_key = get_api_key()
    if not api_key:
        raise ValueError(
            "Gemini API key not found. Check your .streamlit/secrets.toml configuration."
        )

    client = genai.Client(api_key=api_key)
    prompt = """
You are SmartChef AI's ingredient photo assistant. Examine the uploaded photo
and identify only food ingredients that are reasonably visible. Do not guess
hidden ingredients or claim that food is safe to eat from a photo.
Return ONLY a valid JSON array, with no Markdown fences or extra text.
Each item must have these keys:
- name: short, common ingredient name
- confidence: one of High, Medium, Low
- visual_note: brief description of the visual evidence
If no food ingredients can be identified, return an empty array [].
Do not estimate exact weights or quantities from the photo.
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[
            prompt,
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        ],
    )
    response_text = (response.text or "").strip()
    if not response_text:
        raise RuntimeError("The AI returned an empty response. Please try another photo.")

    # Be tolerant if the model accidentally wraps JSON in Markdown fences.
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", response_text, flags=re.IGNORECASE)
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise ValueError("The AI response could not be read. Please try the photo again.")

    data = json.loads(cleaned[start:end + 1])
    if not isinstance(data, list):
        raise ValueError("The AI returned an unexpected result. Please try again.")

    ingredients = []
    for item in data:
        if not isinstance(item, dict) or not str(item.get("name", "")).strip():
            continue
        ingredients.append({
            "name": str(item["name"]).strip(),
            "confidence": str(item.get("confidence", "Uncertain")).strip(),
            "visual_note": str(item.get("visual_note", "")).strip(),
        })
    return ingredients


# -------------------- RECIPE CARD DISPLAY --------------------

def render_recipe_card(recipe_text, key_prefix="recipe"):
    """Render AI recipe Markdown in a cleaner card while keeping original text."""
    lines = recipe_text.splitlines()
    title = "Your SmartChef Recipe"
    title_index = None

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            candidate = re.sub(r"^#+\s*", "", stripped).strip()
            if candidate:
                title = candidate
                title_index = index
                break

    metadata_patterns = {
        "Prep time": r"^(?:[-*]\s*)?(?:\*\*)?(?:preparation time|prep time)(?:\*\*)?\s*[:—-]\s*(.+)$",
        "Cook time": r"^(?:[-*]\s*)?(?:\*\*)?cooking time(?:\*\*)?\s*[:—-]\s*(.+)$",
        "Total time": r"^(?:[-*]\s*)?(?:\*\*)?total time(?:\*\*)?\s*[:—-]\s*(.+)$",
        "Servings": r"^(?:[-*]\s*)?(?:\*\*)?servings(?:\*\*)?\s*[:—-]\s*(.+)$",
        "Difficulty": r"^(?:[-*]\s*)?(?:\*\*)?(?:difficulty|skill level)(?:\*\*)?\s*[:—-]\s*(.+)$",
    }

    metadata = {}
    body_lines = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if index == title_index:
            continue
        matched = False
        for label, pattern in metadata_patterns.items():
            match = re.match(pattern, stripped, flags=re.IGNORECASE)
            if match:
                metadata[label] = match.group(1).strip().strip("*")
                matched = True
                break
        if not matched:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()

    with st.container(border=True):
        st.markdown(
            '<div style="color:#2e8b57;font-size:0.78rem;'
            'font-weight:750;letter-spacing:1.2px;">SMARTCHEF RECIPE</div>',
            unsafe_allow_html=True,
        )
        st.subheader(title)

        if metadata:
            metric_items = list(metadata.items())
            metric_cols = st.columns(min(len(metric_items), 4))
            for index, (label, value) in enumerate(metric_items[:4]):
                with metric_cols[index]:
                    st.metric(label, value)

        st.markdown(body if body else recipe_text)


# -------------------- PAGE HEADER --------------------

st.title("🍲 SmartChef AI")
st.subheader("Cook smarter. Waste less. Eat better.")
st.markdown(
    """
    Your personal kitchen assistant for affordable meals,
    smarter ingredient use, and beginner-friendly cooking.
    """
)
st.caption("AI-POWERED COOKING  ·  PANTRY MANAGEMENT  ·  FOOD WASTE REDUCTION")

pantry = get_pantry()
today = date.today()
soon_limit = today + timedelta(days=3)

expiring_soon = [
    item for item in pantry
    if item["expiry_date"]
    and today <= date.fromisoformat(item["expiry_date"]) <= soon_limit
]

past_dates = [
    item for item in pantry
    if item["expiry_date"]
    and date.fromisoformat(item["expiry_date"]) < today
]

# Keep the current generated recipe during normal Streamlit reruns.
if "latest_recipe" not in st.session_state:
    st.session_state["latest_recipe"] = ""


# -------------------- PANTRY SUMMARY --------------------

metric1, metric2, metric3 = st.columns(3)

metric1.metric("🥕 Pantry items", len(pantry))
metric2.metric("⏰ Use soon", len(expiring_soon))
metric3.metric("❤️ Saved recipes", len(get_favorites()))

st.divider()


# -------------------- MAIN SECTIONS --------------------

recipe_tab, leftover_tab, pantry_tab, favorites_tab, scan_tab, waste_tab = st.tabs([
    "✨ Find Recipes",
    "♻️ Leftover Rescue",
    "🥕 My Kitchen",
    "💗 My Favourites",
    "📸 Scan Ingredients",
    "🌱 Food Waste Tracker",
])


# -------------------- FIND RECIPES --------------------

with recipe_tab:
    st.header("What can I cook today?")
    st.write(
        "Use ingredients from your kitchen, add anything else "
        "you have, and let AI suggest a recipe."
    )

    with st.sidebar:
        st.header("Recipe preferences")

        cuisine = st.selectbox(
            "Cuisine",
            [
                "Indian", "Italian", "Chinese", "Mexican",
                "Mediterranean", "Any cuisine",
            ],
        )

        diet = st.selectbox(
            "Dietary preference",
            [
                "No specific preference", "Vegetarian", "Vegan",
                "Eggetarian", "High-protein",
                "Gluten-free preference",
            ],
        )

        meal_type = st.selectbox(
            "Meal type",
            [
                "Any meal", "Breakfast", "Lunch",
                "Dinner", "Snack", "Dessert",
            ],
        )

        time_limit = st.slider(
            "Maximum cooking time (minutes)",
            10, 120, 30, step=5,
        )

        servings = st.number_input(
            "Number of servings",
            min_value=1, max_value=12, value=1, step=1,
        )

        skill = st.selectbox(
            "Cooking skill",
            ["Beginner", "Intermediate", "Advanced"],
        )

        budget = st.selectbox(
            "Budget for additional ingredients",
            ["No extra spending", "Up to ₹30", "Up to ₹50", "Up to ₹100"],
        )

        st.divider()
        st.subheader("🎓 Student Budget Mode")
        student_budget_mode = st.checkbox(
            "Enable Student Budget Mode",
            value=False,
            help=(
                "Ask AI to prioritize low-cost meals, use pantry ingredients "
                "first, and estimate the cost per serving."
            ),
        )

        student_budget_limit = st.selectbox(
            "Target budget per serving",
            [30, 50, 75, 100, 150],
            format_func=lambda amount: f"₹{amount}",
            index=1,
            disabled=not student_budget_mode,
        )

        if student_budget_mode:
            st.caption(
                "Costs are AI estimates; actual prices vary by shop, "
                "brand, location, and season."
            )

    pantry_text = "\n".join(
        f"- {item['name']}: {item['quantity']:g} {item['unit']}"
        for item in pantry
    )

    if pantry:
        st.success(
            f"Your pantry has {len(pantry)} item(s). "
            "We'll include them in your recipe request."
        )
    else:
        st.info(
            "Your pantry is empty for now. You can add ingredients "
            "in the My Kitchen tab or type them below."
        )

    ingredients = st.text_area(
        "What other ingredients do you have?",
        placeholder="Example: potatoes, onion, tomato, rice",
        height=100,
    )

    prioritize_soon = st.checkbox(
        "Prioritize ingredients that need to be used soon",
        value=True,
    )

    extra_notes = st.text_input(
        "Anything else? (optional)",
        placeholder="Example: less spicy, one pan, no oven",
    )

    generate = st.button(
        "✨ Find My Recipe",
        type="primary",
        use_container_width=True,
    )

    if generate:
        if not pantry and len(ingredients.strip()) < 3:
            st.warning(
                "Add ingredients to My Kitchen or enter some above "
                "before generating a recipe."
            )
        else:
            combined_ingredients = pantry_text

            if ingredients.strip():
                combined_ingredients += (
                    "\nAdditional ingredients provided now:\n"
                    + ingredients.strip()
                )

            notes = extra_notes.strip()
            notes += f"\nBudget for additional ingredients: {budget}."

            if student_budget_mode:
                notes += (
                    f"\nSTUDENT BUDGET MODE IS ENABLED. Keep the estimated "
                    f"total ingredient cost at or below ₹{student_budget_limit} "
                    "per serving where practical. Prioritize ingredients already "
                    "in the user's pantry, use inexpensive and commonly available "
                    "ingredients, suggest economical substitutions, and avoid "
                    "specialty ingredients. Include an estimated cost per serving "
                    "and a simple cost breakdown for only the ingredients that "
                    "need to be purchased. Clearly label all prices as estimates "
                    "that vary by location and shop. Do not claim exact live prices."
                )

            if prioritize_soon and expiring_soon:
                soon_names = ", ".join(
                    item["name"] for item in expiring_soon
                )
                notes += (
                    "\nPrioritize using these ingredients where suitable: "
                    + soon_names
                    + "."
                )

            if past_dates:
                past_names = ", ".join(
                    item["name"] for item in past_dates
                )
                notes += (
                    "\nThese pantry items have dates in the past: "
                    + past_names
                    + ". Do not assume they are safe or recommend them "
                    "without appropriate food-safety checks."
                )

            try:
                with st.spinner("Finding something delicious..."):
                    recipe = generate_recipe(
                        ingredients=combined_ingredients,
                        cuisine=cuisine,
                        diet=diet,
                        meal_type=meal_type,
                        time_limit=time_limit,
                        servings=int(servings),
                        skill=skill,
                        extra_notes=notes,
                    )

                st.session_state["latest_recipe"] = recipe

            except Exception as exc:
                st.error(f"Recipe generation failed: {exc}")
                st.caption(
                    "Check your connection, API key, model access "
                    "and API quota."
                )

    if st.session_state["latest_recipe"]:
        st.divider()
        render_recipe_card(
            st.session_state["latest_recipe"],
            key_prefix="latest_recipe",
        )

        st.download_button(
            "📄 Download recipe as TXT",
            data=st.session_state["latest_recipe"],
            file_name="smartchef_recipe.txt",
            mime="text/plain",
        )

        if st.button("❤️ Save to Favourites", key="save_latest"):
            add_favorite(st.session_state["latest_recipe"])
            st.success("Recipe saved to your favourites!")
            st.rerun()

    st.caption(
        "AI suggestions are estimates. Check ingredient labels, "
        "allergens and food-safety guidance before cooking."
    )

# -------------------- LEFTOVER RESCUE --------------------

with leftover_tab:
    st.header("♻️ Leftover Rescue")
    st.write(
        "Turn yesterday's rice, dal and cooked vegetables into "
        "a fresh meal. Save food, save money, and cook smarter."
    )

    st.info(
        "Only use leftovers that have been stored safely. "
        "Refrigerate perishable leftovers promptly, generally within "
        "2 hours (within 1 hour in temperatures above 32°C). "
        "When in doubt, throw them out."
    )

    leftover_types = st.multiselect(
        "What leftovers do you have?",
        [
            "Cooked rice",
            "Cooked dal",
            "Cooked vegetables",
            "Cooked potatoes",
            "Roti or chapati",
            "Cooked pasta",
            "Cooked beans",
            "Other leftovers",
        ],
        placeholder="Select your leftover foods",
        key="leftover_types",
    )

    leftover_details = st.text_area(
        "Describe your leftovers and quantities",
        placeholder=(
            "Example: 1 bowl of cooked rice, half a bowl of dal, "
            "some cooked carrots and peas"
        ),
        height=100,
        key="leftover_details",
    )

    storage_status = st.selectbox(
        "How were the leftovers stored?",
        [
            "Refrigerated promptly",
            "Frozen promptly",
            "At room temperature within 2 hours "
            "(within 1 hour above 32°C)",
            "Left at room temperature too long",
            "Not sure how they were stored",
        ],
        key="leftover_storage",
    )

    st.caption(
        "For room-temperature storage, use the stricter one-hour "
        "limit in temperatures above 32°C. Cooked rice needs "
        "particular care because some bacterial toxins may survive "
        "reheating."
    )

    include_pantry = st.checkbox(
        "Also use ingredients from My Kitchen",
        value=True,
        key="leftover_include_pantry",
    )

    rescue_time = st.slider(
        "Maximum cooking time (minutes)",
        min_value=5,
        max_value=60,
        value=20,
        step=5,
        key="leftover_time",
    )

    rescue_servings = st.number_input(
        "How many servings?",
        min_value=1,
        max_value=6,
        value=1,
        step=1,
        key="leftover_servings",
    )

    rescue_button = st.button(
        "♻️ Rescue My Leftovers",
        type="primary",
        use_container_width=True,
        key="rescue_leftovers_button",
    )

    if rescue_button:
        if not leftover_types:
            st.warning("Please select at least one type of leftover.")
        elif len(leftover_details.strip()) < 3:
            st.warning(
                "Please describe your leftovers and their quantities."
            )
        elif storage_status in [
            "Left at room temperature too long",
            "Not sure how they were stored",
        ]:
            st.error(
                "For safety, don't use leftovers that may have been "
                "stored unsafely. AI cannot determine whether food "
                "is safe to eat."
            )
        else:
            leftover_ingredients = (
                "LEFTOVERS THAT SHOULD BE THE MAIN INGREDIENTS:\n"
                + leftover_details.strip()
                + "\nTypes selected: "
                + ", ".join(leftover_types)
            )

            if include_pantry and pantry:
                # Do not suggest pantry ingredients whose recorded
                # date has already passed as optional recipe ingredients.
                safe_date_pantry = [
                    item for item in pantry
                    if not item["expiry_date"]
                    or date.fromisoformat(item["expiry_date"]) >= today
                ]

                pantry_additions = "\n".join(
                    f"- {item['name']}: "
                    f"{item['quantity']:g} {item['unit']}"
                    for item in safe_date_pantry
                )

                if pantry_additions:
                    leftover_ingredients += (
                        "\n\nOPTIONAL INGREDIENTS FROM THE USER'S PANTRY:\n"
                        + pantry_additions
                    )

            safety_note = (
                "Create a leftover-rescue recipe for a student living "
                "alone. Use the described leftovers as the main "
                "ingredients. Prefer simple, affordable meals, minimal "
                "equipment and minimal washing up. Clearly identify "
                "any extra ingredients needed. Give beginner-friendly "
                "steps and safe reheating instructions. For leftovers "
                "that require reheating, advise heating throughout to "
                "74°C (165°F). Never claim that reheating makes "
                "improperly stored food safe. Do not recommend "
                "ingredients that may be unsafe."
            )

            if student_budget_mode:
                safety_note += (
                    f" Student Budget Mode is enabled: keep additional "
                    f"purchases within an estimated ₹{student_budget_limit} "
                    "per serving where practical, use pantry items first, "
                    "and include estimated per-serving cost plus a simple "
                    "breakdown of ingredients to buy. Prices are estimates, "
                    "not live market prices."
                )

            if storage_status == "Frozen promptly":
                safety_note += (
                    " The user reports that the leftovers were frozen "
                    "promptly. Explain safe thawing and reheating."
                )
            elif storage_status == "Refrigerated promptly":
                safety_note += (
                    " The user reports prompt refrigeration. Remind "
                    "them to check storage duration and food-safety "
                    "guidance before using the leftovers."
                )
            else:
                safety_note += (
                    " The user reports short room-temperature storage. "
                    "Only proceed if the food stayed within safe time "
                    "and temperature limits; otherwise discard it."
                )

            try:
                with st.spinner(
                    "Finding a delicious way to reuse your leftovers..."
                ):
                    rescued_recipe = generate_recipe(
                        ingredients=leftover_ingredients,
                        cuisine=cuisine,
                        diet=diet,
                        meal_type="Any meal",
                        time_limit=rescue_time,
                        servings=int(rescue_servings),
                        skill="Beginner",
                        extra_notes=safety_note,
                    )

                st.session_state["leftover_recipe"] = rescued_recipe

            except Exception as exc:
                st.error(f"Leftover recipe generation failed: {exc}")
                st.caption(
                    "Check your internet connection, API key, "
                    "model access and API quota."
                )

    if st.session_state.get("leftover_recipe"):
        st.divider()
        render_recipe_card(
            st.session_state["leftover_recipe"],
            key_prefix="leftover_recipe",
        )

        st.download_button(
            "📄 Download leftover recipe",
            data=st.session_state["leftover_recipe"],
            file_name="smartchef_leftover_recipe.txt",
            mime="text/plain",
            key="download_leftover_recipe",
        )

        if st.button(
            "❤️ Save leftover recipe to Favourites",
            key="save_leftover_recipe",
        ):
            add_favorite(st.session_state["leftover_recipe"])
            st.success("Leftover recipe saved to your favourites!")
            st.rerun()


# -------------------- MY KITCHEN --------------------

with pantry_tab:
    st.header("🥕 My Kitchen")
    st.write(
        "Keep track of ingredients you have at home, how much is "
        "left, and their dates."
    )

    with st.form("add_ingredient_form"):
        st.subheader("Add an ingredient")

        item_name = st.text_input(
            "Ingredient name",
            placeholder="Example: spinach",
        )

        col1, col2 = st.columns(2)

        with col1:
            quantity = st.number_input(
                "Quantity",
                min_value=0.1,
                max_value=10000.0,
                value=1.0,
                step=0.5,
            )

        with col2:
            unit = st.selectbox(
                "Unit",
                [
                    "pieces", "g", "kg", "ml", "litres",
                    "packets", "cups", "tablespoons", "other",
                ],
            )

        has_expiry = st.checkbox(
            "Add a use-by / expiry date"
        )

        expiry = None

        if has_expiry:
            expiry = st.date_input(
                "Date shown on the package",
                value=today + timedelta(days=7),
                min_value=date(2000, 1, 1),
                max_value=date(2100, 12, 31),
            )

        submitted = st.form_submit_button(
            "➕ Add to My Kitchen",
            type="primary",
        )

        if submitted:
            if not item_name.strip():
                st.warning("Please enter an ingredient name.")
            else:
                add_ingredient(
                    item_name,
                    quantity,
                    unit,
                    expiry,
                )
                st.success(f"{item_name.strip()} added to your kitchen!")
                st.rerun()

    st.divider()
    st.subheader("⏰ Use Soon")

    if expiring_soon:
        st.write(
            "These items have dates today or within the next three days."
        )

        for item in expiring_soon:
            expiry_day = date.fromisoformat(item["expiry_date"])
            days_left = (expiry_day - today).days

            if days_left == 0:
                label = "Date is today"
            else:
                label = f"{days_left} day(s) until date"

            st.warning(
                f"**{item['name']}** — "
                f"{item['quantity']:g} {item['unit']} · {label}"
            )
    else:
        st.info(
            "No ingredients with dates in the next three days. "
            "Add dates when entering your pantry items."
        )

    if past_dates:
        st.divider()
        st.subheader("⚠️ Check these dates")

        for item in past_dates:
            st.warning(
                f"**{item['name']}** — date recorded: "
                f"{item['expiry_date']}. Check the product label and "
                "appropriate food-safety guidance; do not assume it "
                "is safe to eat."
            )

    st.divider()
    st.subheader("All pantry ingredients")

    if pantry:
        for item in pantry:
            col1, col2, col3 = st.columns([3, 2, 1])

            with col1:
                st.write(f"**{item['name']}**")

            with col2:
                st.write(
                    f"{item['quantity']:g} {item['unit']}"
                )
                if item["expiry_date"]:
                    st.caption(f"Date: {item['expiry_date']}")
                else:
                    st.caption("No date entered")

            with col3:
                if st.button(
                    "🗑️ Remove",
                    key=f"delete_item_{item['id']}",
                ):
                    delete_ingredient(item["id"])
                    st.rerun()

            st.divider()
    else:
        st.info("Your kitchen is empty. Add your first ingredient above.")


# -------------------- MY FAVOURITES --------------------

with favorites_tab:
    st.header("❤️ My Favourite Recipes")

    favorites = get_favorites()

    if favorites:
        for favorite in favorites:
            with st.expander(
                f"Recipe saved on {favorite['created_at']}"
            ):
                render_recipe_card(
                    favorite["recipe"],
                    key_prefix=f"favorite_{favorite['id']}",
                )

                st.download_button(
                    "⬇️ Download recipe",
                    data=favorite["recipe"],
                    file_name=f"favorite_recipe_{favorite['id']}.txt",
                    mime="text/plain",
                    key=f"download_fav_{favorite['id']}",
                )

                if st.button(
                    "🗑️ Remove from Favourites",
                    key=f"remove_fav_{favorite['id']}",
                ):
                    delete_favorite(favorite["id"])
                    st.rerun()
    else:
        st.info(
            "No favourites yet. Generate a recipe and save it "
            "using the ❤️ button."
        )


# -------------------- INGREDIENT PHOTO RECOGNITION --------------------

with scan_tab:
    st.header("📸 Identify Ingredients from a Photo")
    st.write(
        "Upload a clear photo of your groceries or kitchen counter. Gemini will "
        "suggest visible ingredients, and you can review each suggestion before "
        "adding it to My Kitchen."
    )
    st.info(
        "Photo recognition is an estimate, not a guarantee. Check every result "
        "yourself. The AI cannot reliably determine exact quantities, hidden "
        "ingredients, freshness, or food safety from an image."
    )

    uploaded_image = st.file_uploader(
        "Choose an ingredient photo",
        type=["jpg", "jpeg", "png", "webp"],
        help="Use JPG, JPEG, PNG, or WEBP. A clear, well-lit photo works best.",
        key="ingredient_photo_upload",
    )

    if uploaded_image is not None:
        image_bytes = uploaded_image.getvalue()
        if len(image_bytes) > 10 * 1024 * 1024:
            st.error("Please choose an image smaller than 10 MB.")
        else:
            st.image(image_bytes, caption="Photo to inspect", use_container_width=True)
            if st.button("🔎 Identify visible ingredients", type="primary", key="detect_ingredients_button"):
                with st.spinner("Looking for visible ingredients…"):
                    try:
                        detected = detect_ingredients_from_image(
                            image_bytes,
                            uploaded_image.type or "image/jpeg",
                        )
                        st.session_state["detected_photo_ingredients"] = detected
                        st.session_state["detected_photo_signature"] = (
                            uploaded_image.name,
                            len(image_bytes),
                        )
                    except Exception as exc:
                        error_text = str(exc)
                        if any(code in error_text.upper() for code in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")):
                            st.error("Gemini is busy right now. Wait a moment and try again.")
                        else:
                            st.error(f"Could not identify ingredients: {error_text}")

    detected_ingredients = st.session_state.get("detected_photo_ingredients", [])
    if detected_ingredients:
        st.divider()
        st.subheader("AI suggestions — please review")
        for ingredient in detected_ingredients:
            st.markdown(f"**{ingredient['name']}** · Confidence: {ingredient['confidence']}")
            if ingredient.get("visual_note"):
                st.caption(ingredient["visual_note"])
        st.caption("Confidence describes the model's visual estimate, not a verified probability.")

        st.divider()
        st.subheader("Add one reviewed ingredient to My Kitchen")
        ingredient_names = [item["name"] for item in detected_ingredients]
        with st.form("add_detected_ingredient_form"):
            selected_name = st.selectbox("Choose an ingredient to add", ingredient_names)
            add_col1, add_col2 = st.columns(2)
            with add_col1:
                photo_quantity = st.number_input(
                    "Quantity (check and enter it yourself)",
                    min_value=0.1,
                    max_value=10000.0,
                    value=1.0,
                    step=0.5,
                )
            with add_col2:
                photo_unit = st.selectbox(
                    "Unit",
                    ["pieces", "g", "kg", "ml", "litres", "packets", "cups", "tablespoons", "other"],
                    key="photo_ingredient_unit",
                )
            photo_has_expiry = st.checkbox("Add a use-by / expiry date", key="photo_has_expiry")
            photo_expiry = None
            if photo_has_expiry:
                photo_expiry = st.date_input(
                    "Date shown on the package",
                    value=today + timedelta(days=7),
                    min_value=date(2000, 1, 1),
                    max_value=date(2100, 12, 31),
                    key="photo_ingredient_expiry",
                )
            add_detected = st.form_submit_button("➕ Add reviewed ingredient to My Kitchen", type="primary")
            if add_detected:
                add_ingredient(selected_name, photo_quantity, photo_unit, photo_expiry)
                st.success(f"Added {selected_name} to My Kitchen. Please verify the quantity and date in the pantry.")
                st.rerun()
    elif uploaded_image is not None:
        st.caption("After identification, detected ingredients will appear here for review.")
    else:
        st.caption("Tip: spread ingredients out, use good lighting, and avoid blurry or very crowded photos.")


# -------------------- FOOD WASTE TRACKER --------------------

with waste_tab:
    st.header("🌱 Food Waste Tracker")
    st.write(
        "Record ingredients you rescued or had to discard. Over time, "
        "this log helps you understand patterns and reduce avoidable waste."
    )
    st.caption(
        "Entries are based on what you record; the app does not automatically "
        "weigh food or verify that an ingredient was actually consumed."
    )

    with st.form("waste_log_form", clear_on_submit=True):
        st.subheader("Log an ingredient")
        waste_col1, waste_col2 = st.columns(2)
        with waste_col1:
            waste_item = st.text_input(
                "Ingredient or leftover name",
                placeholder="e.g. cooked rice, spinach, dal",
            )
            waste_quantity = st.number_input(
                "Quantity", min_value=0.1, max_value=10000.0,
                value=1.0, step=0.5,
            )
            waste_unit = st.selectbox(
                "Unit", ["pieces", "g", "kg", "ml", "litres", "cups", "bowls", "packets", "other"]
            )
        with waste_col2:
            waste_action = st.radio(
                "What happened to it?", ["Rescued", "Wasted"], horizontal=True,
                help="Rescued = reused or consumed instead of being discarded. Wasted = discarded."
            )
            waste_date = st.date_input("Date", value=date.today(), key="waste_log_date")
            waste_reason = st.text_input(
                "Notes (optional)",
                placeholder="e.g. used in fried rice / spoiled before use",
            )
        log_submitted = st.form_submit_button("➕ Save Tracker Entry", type="primary")
        if log_submitted:
            if not waste_item.strip():
                st.warning("Please enter an ingredient name.")
            else:
                log_waste_event(
                    waste_item, waste_quantity, waste_unit,
                    waste_action, waste_reason, waste_date,
                )
                st.success(f"{waste_item.strip()} logged as {waste_action.lower()}.")
                st.rerun()

    entries = get_waste_log()
    today = date.today()
    month_start = today.replace(day=1)
    month_entries = [e for e in entries if date.fromisoformat(e["logged_date"]) >= month_start]
    rescued_count = sum(1 for e in entries if e["action"] == "Rescued")
    wasted_count = sum(1 for e in entries if e["action"] == "Wasted")
    month_rescued = sum(1 for e in month_entries if e["action"] == "Rescued")
    month_wasted = sum(1 for e in month_entries if e["action"] == "Wasted")

    st.divider()
    st.subheader("Your waste-reduction overview")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("♻️ Rescued entries", rescued_count)
    m2.metric("🗑️ Wasted entries", wasted_count)
    m3.metric("This month · rescued", month_rescued)
    m4.metric("This month · wasted", month_wasted)
    st.caption("Counts represent logged entries, not measured weight or money saved.")

    if rescued_count + wasted_count:
        total_entries = rescued_count + wasted_count
        rescue_percent = round(rescued_count / total_entries * 100)
        st.progress(rescue_percent / 100, text=f"{rescue_percent}% of logged entries marked rescued")

    st.divider()
    st.subheader("Recent entries")
    if entries:
        st.download_button(
            "⬇️ Export tracker as CSV",
            data=waste_log_csv(entries),
            file_name="smartchef_food_waste_log.csv",
            mime="text/csv",
            key="download_waste_log_csv",
        )
        for event in entries:
            with st.container(border=True):
                row_col1, row_col2, row_col3 = st.columns([3, 2, 1])
                with row_col1:
                    symbol = "♻️" if event["action"] == "Rescued" else "🗑️"
                    st.markdown(f"**{symbol} {event['item_name']}**")
                    st.caption(event["reason"] or "No notes added")
                with row_col2:
                    st.write(f"{event['quantity']:g} {event['unit']} · {event['action']}")
                    st.caption(event["logged_date"])
                with row_col3:
                    if st.button("Remove", key=f"delete_waste_{event['id']}"):
                        delete_waste_event(event["id"])
                        st.rerun()
    else:
        st.info("No entries yet. Log your first rescued or wasted ingredient above.")


# -------------------- FOOTER --------------------

st.divider()
st.caption("SmartChef AI · Cook smart, save money, waste less.")