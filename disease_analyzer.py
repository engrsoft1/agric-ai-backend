import os
import json
from PIL import Image
from google import genai
from dotenv import load_dotenv

# Load .env file
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=API_KEY)


# --------------------------------------------
# Analyze Crop Image
# --------------------------------------------

def analyze_crop_image(image_path: str):

    image = Image.open(image_path)

    prompt = """
You are an expert agricultural diagnostic AI.

You can diagnose:

1. Crop diseases
2. Poultry diseases
3. Livestock diseases
4. Aquaculture (fish) diseases

Analyze the uploaded image carefully.

Respond ONLY in valid JSON.

Use EXACTLY this format:

{
  "category": "",
  "name": "",
  "condition": "",
  "confidence": "",
  "severity": "",
  "cause": "",
  "symptoms": [],
  "treatments": [],
  "prevention": []
}

Rules:

category must be one of:

- Crop
- Poultry
- Livestock
- Aquaculture
- Unknown

Examples:

Crop
------
name: Tomato
condition: Early Blight

Crop
------
name: Maize
condition: Healthy Plant

Poultry
---------
name: Chicken
condition: Fowl Pox

Livestock
-----------
name: Goat
condition: Mange

Aquaculture
--------------
name: Catfish
condition: Fin Rot

If healthy:

condition = "Healthy"

confidence must be percentage such as:

"97%"

severity must be exactly one of:

Low
Moderate
High
Severe
None

If Healthy:
severity = "None"

Symptoms:
- 3 to 5 items

Treatments:
- 3 to 5 items

Prevention:
- 3 to 5 items

If the image is unclear:

category = "Unknown"
name = "Unknown"
condition = "Unable to Identify"

Return ONLY valid JSON.

Do not include markdown.
Do not include explanations.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            prompt,
            image,
        ],
    )

    print("\n========== GEMINI RESPONSE ==========")
    print(response)
    print("=====================================\n")

    print("\n========== RESPONSE.TEXT ==========")
    print(response.text)
    print("===================================\n")

    text = response.text.strip()

    if text.startswith("```json"):
        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

    return json.loads(text)