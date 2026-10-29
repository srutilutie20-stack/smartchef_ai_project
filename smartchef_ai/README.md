# SmartChef AI — AI Recipe Generator

A beginner-friendly NTCC project built with Python, Streamlit, and Google's Gemini API. Users enter available ingredients and select cuisine, dietary preference, meal type, cooking time, serving size, and skill level. The application sends these details to a generative AI model and displays a recipe in Markdown.

## Features

- Ingredient-based recipe generation
- Cuisine and dietary preference options
- Meal type, cooking-time limit, servings, and skill-level controls
- Beginner-friendly recipe steps and quantities
- Error handling for missing API key and failed generation
- Download generated recipe as a Markdown file
- API key loaded from Streamlit secrets or an environment variable

## Requirements

- Python 3.10 or newer (Python 3.11 or 3.12 recommended)
- VS Code or another editor
- Internet connection
- Gemini API key with access to the selected model

## Run on Windows (PowerShell)

1. Extract the project folder and open it in VS Code.
2. Open Terminal → New Terminal.
3. Create a virtual environment:

   ```powershell
   py -m venv .venv
   ```

4. Activate it:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use Command Prompt and run `.venv\Scripts\activate.bat`, or run the venv's Python directly as shown below.

5. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

6. Create your API key at the official Google AI Studio site: https://aistudio.google.com/app/apikey
7. Create a folder named `.streamlit` if it does not already exist. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and replace the placeholder with your key:

   ```toml
   GEMINI_API_KEY = "your_real_api_key"
   ```

8. Start the app:

   ```powershell
   streamlit run app.py
   ```

9. Open the local URL printed in the terminal (usually `http://localhost:8501`).

### Alternative: environment variable

Instead of a secrets file, set the key in the current PowerShell session:

```powershell
$env:GEMINI_API_KEY = "your_real_api_key"
streamlit run app.py
```

Never commit your API key to GitHub or paste it into a public report, screenshot, or presentation.

## Project structure

```text
smartchef_ai/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
└── .streamlit/
    └── secrets.toml.example
```

## Troubleshooting

- **`streamlit` is not recognized:** activate the virtual environment, or run `python -m streamlit run app.py`.
- **API key not found:** check that `.streamlit/secrets.toml` exists in the project and the key name is exactly `GEMINI_API_KEY`.
- **Invalid API key / permission error:** verify the key and that the selected model is available for your account.
- **Quota or rate-limit error:** check the provider's current quota and billing/usage settings; retry later if appropriate.
- **Module not found:** activate the environment and run `pip install -r requirements.txt`.
- **Model unavailable:** update `model="gemini-2.5-flash"` in `app.py` to a currently supported model available to your API key, following the provider's current documentation.

## How it works

1. Streamlit collects ingredients and user preferences.
2. Python validates that ingredients were provided.
3. `generate_recipe()` builds a prompt containing user inputs and recipe instructions.
4. The Gemini API generates a text response.
5. Streamlit renders the response and provides a Markdown download.

## Important limitations

- AI output may be inaccurate or inconsistent; verify quantities and cooking instructions.
- The prototype does not calculate verified nutrition values or guarantee allergy safety.
- It does not yet include login, a database, saved recipe history, image generation, or automated ingredient inventory. These are optional future enhancements.

## Deployment

Push the project to GitHub **without** `.streamlit/secrets.toml`. In Streamlit Community Cloud, create an app from the repository, set `app.py` as the entrypoint, and add `GEMINI_API_KEY` under the app's Secrets settings. See the official documentation: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app and https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
