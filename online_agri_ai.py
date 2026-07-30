# ============================================================
# AgriAI Version 3.1.0
# Cloud AI Engine
# Powered by Google Gemini
# ============================================================

import os

from dotenv import load_dotenv
from langdetect import detect
from google import genai

# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found.")

client = genai.Client(api_key=API_KEY)

# ============================================================
# MEMORY
# ============================================================

conversation_history = []

# ============================================================
# SUPPORTED LANGUAGES
# ============================================================

SUPPORTED_LANGUAGES = {
    "en": "English",
    "ha": "Hausa",
    "yo": "Yoruba",
    "ig": "Igbo",
}

# ============================================================
# LANGUAGE DETECTION
# ============================================================

def detect_language(text):

    text = text.lower()

    hausa_words = [
        "noma",
        "gona",
        "masara",
        "shanu",
        "kaza",
        "ruwa",
        "ina",
        "yaya"
    ]

    yoruba_words = [
        "agbado",
        "oko",
        "adie",
        "ewa",
        "bawo"
    ]

    igbo_words = [
        "ugbo",
        "oka",
        "ewu",
        "kedu"
    ]

    if any(word in text for word in hausa_words):
        return "ha"

    if any(word in text for word in yoruba_words):
        return "yo"

    if any(word in text for word in igbo_words):
        return "ig"

    try:
        lang = detect(text)

        if lang in SUPPORTED_LANGUAGES:
            return lang

    except Exception:
        pass

    return "en"


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are AgriAI.

You are an Agriculture Assistant developed for IITA (I-YOUTH).

Rules:

1. Answer ONLY agriculture questions.

2. Agriculture includes:
- Crops
- Livestock
- Poultry
- Fisheries
- Irrigation
- Soil
- Fertilizer
- Farm machinery
- Agricultural economics
- Extension services
- Climate-smart agriculture
- Pest control
- Weed control
- Animal health

3.  If a user asks about medicine,
politics,
sports,
religion,
programming,
relationships,
history,
or any non-agricultural topic, 

4.  Politely reply that AgriAI only provides agricultural assistance.

5. Never answer outside agriculture.

6. Always respond in the same language used by the user.

7. Keep answers practical,
simple,
accurate,
and farmer-friendly.

8. Never invent facts.

9. When appropriate:
- Give treatment steps.
- Give prevention methods.
- Recommend good farming practices.
"""

# ============================================================
# AI RESPONSE
# ============================================================

def get_online_answer(user_input):

    global conversation_history

    language = detect_language(user_input)

    conversation_history.append(
        {
            "role": "user",
            "text": user_input,
        }
    )

    # Keep only last 20 exchanges
    conversation_history = conversation_history[-20:]

    history = ""

    for item in conversation_history:
        history += f"{item['role']}: {item['text']}\n"

    prompt = f"""
{SYSTEM_PROMPT}

Conversation History:

{history}

Current User Question:

{user_input}
"""

    try:

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        answer = response.text.strip()

        conversation_history.append(
            {
                "role": "assistant",
                "text": answer,
            }
        )

        return {
            "success": True,
            "language": language,
            "answer": answer,
        }

    except Exception as e:

        return {
            "success": False,
            "language": language,
            "answer": f"The AI service is temporarily unavailable, Please try again later: {e}",
        }