import os
import streamlit as st
from google import genai

st.set_page_config(page_title="SmartChef AI", page_icon="🍲", layout="wide")

# Read the API key from Streamlit secrets or an environment variable.
def get_api_key():
    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        key = ""
    return key or os.getenv("GEMINI_API_KEY", "")


def generate_recipe(ingredients, cuisine, diet, meal_type, time_limit, servings, skill, extra_notes):
    api_key = get_api_key()
    if not api_key:
        raise ValueError(
            "Gemini API key not found. Add GEMINI_API_KEY to .streamlit/secrets.toml "
            "or set it as an environment variable. See README.md."
        )

    client = genai.Client(api_key=api_key)
    prompt = f"""
You are SmartChef AI, a careful recipe assistant. Create one practical recipe using the user's details.

User details:
- Ingredients available: {ingredients}
- Preferred cuisine: {cuisine}
- Dietary preference: {diet}
- Meal type: {meal_type}
- Maximum total time: {time_limit} minutes
- Servings: {servings}
- Cooking skill: {skill}
- Extra requests: {extra_notes or 'None'}

Requirements:
1. Give a clear recipe title and a short description.
2. List ingredients with quantities, using common kitchen measures where possible.
3. List numbered, beginner-friendly preparation steps.
4. Include estimated preparation time, cooking time, total time, servings, and difficulty.
5. Mention reasonable substitutions and serving suggestions.
6. Prefer the listed ingredients; identify any additional pantry ingredients clearly.
7. Do not claim the recipe is medically suitable for allergies or illnesses. Flag likely allergens when relevant.
8. Include a short food-safety note where relevant, especially for meat, eggs, and seafood.
9. Do not invent nutrition numbers. If giving nutrition, clearly label it as an estimate.
10. Format the response in readable Markdown with headings.
"""
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt,
    )
    if not response.text:
        raise RuntimeError("The AI returned an empty response. Please try again.")
    return response.text


st.title("🍲 SmartChef AI")
st.subheader("Your ingredients. Your preferences. A recipe made for you.")
st.write("Generate personalized recipe ideas with generative AI. Review ingredients and cooking instructions before preparing any dish.")

with st.sidebar:
    st.header("Recipe preferences")
    cuisine = st.selectbox("Cuisine", ["Indian", "Italian", "Chinese", "Mexican", "Mediterranean", "Any cuisine"])
    diet = st.selectbox("Dietary preference", ["No specific preference", "Vegetarian", "Vegan", "Eggetarian", "High-protein", "Gluten-free preference"])
    meal_type = st.selectbox("Meal type", ["Any meal", "Breakfast", "Lunch", "Dinner", "Snack", "Dessert"])
    time_limit = st.slider("Maximum total time (minutes)", 10, 120, 30, step=5)
    servings = st.number_input("Number of servings", min_value=1, max_value=12, value=2, step=1)
    skill = st.selectbox("Cooking skill", ["Beginner", "Intermediate", "Advanced"])

left, right = st.columns([3, 2])
with left:
    ingredients = st.text_area(
        "🥕 What ingredients do you have?",
        placeholder="Example: potatoes, onion, tomato, peas, rice, curd",
        height=120,
    )
    extra_notes = st.text_input(
        "Anything else? (optional)",
        placeholder="Example: less spicy, no oven, use leftover rice",
    )
    generate = st.button("✨ Generate my recipe", type="primary", use_container_width=True)
with right:
    st.markdown("### How it works")
    st.markdown("1. Enter ingredients you have.\n2. Choose your cuisine and preferences.\n3. Generate a recipe with AI.\n4. Review the quantities and steps before cooking.")
    st.info("AI-generated recipes can contain mistakes. Check ingredient labels and cook food to safe temperatures.")

if generate:
    if len(ingredients.strip()) < 3:
        st.warning("Please enter at least one ingredient so the AI can personalize your recipe.")
    else:
        try:
            with st.spinner("Creating a recipe for you..."):
                recipe = generate_recipe(
                    ingredients=ingredients.strip(), cuisine=cuisine, diet=diet,
                    meal_type=meal_type, time_limit=time_limit, servings=int(servings),
                    skill=skill, extra_notes=extra_notes.strip()
                )
            st.session_state["latest_recipe"] = recipe
            st.session_state["latest_inputs"] = {
                "ingredients": ingredients, "cuisine": cuisine, "diet": diet,
                "meal_type": meal_type, "time_limit": time_limit, "servings": servings,
            }
        except Exception as exc:
            st.error(f"Recipe generation failed: {exc}")
            st.caption("Check your internet connection, API key, model access, and API quota, then try again.")

if st.session_state.get("latest_recipe"):
    st.divider()
    st.markdown("## 🍽️ Your generated recipe")
    st.markdown(st.session_state["latest_recipe"])
    st.download_button(
        "⬇️ Download recipe as Markdown",
        data=st.session_state["latest_recipe"],
        file_name="smartchef_recipe.md",
        mime="text/markdown",
        use_container_width=False,
    )

with st.expander("About this NTCC project"):
    st.write("SmartChef AI is a generative-AI web application. The user provides ingredients and preferences; the application builds a prompt, sends it to a language model, and displays the generated recipe. This prototype does not verify nutritional or medical claims and does not guarantee allergy safety.")

st.caption("NTCC Project Prototype · SmartChef AI")
