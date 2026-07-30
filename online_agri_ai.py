# ============================================================
# AgriAI Version 3.0
# Online Agriculture AI Assistant
# English | Hausa | Yoruba | Igbo
# Powered by Google Gemini
# ============================================================

import os
import tempfile

import speech_recognition as sr
from gtts import gTTS
from playsound import playsound
from langdetect import detect

from google import genai



# ============================================================
# GEMINI API KEY
# ============================================================

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")

client = genai.Client(api_key=API_KEY)
# ============================================================
# MEMORY
# ============================================================

conversation_history = []


# ============================================================
# SUPPORTED LANGUAGES
# ============================================================

SUPPORTED_LANGUAGES = {

    "en": {
        "name": "English",
        "voice": "en",
        "speech": "en-US"
    },

    "ha": {
        "name": "Hausa",
        "voice": "ha",
        "speech": "ha-NG"
    },

    "yo": {
        "name": "Yoruba",
        "voice": "yo",
        "speech": "yo-NG"
    },

    "ig": {
        "name": "Igbo",
        "voice": "ig",
        "speech": "ig-NG"
    }

}


# ============================================================
# NORMALIZE
# ============================================================

def normalize_text(text):
    return text.lower().strip()


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

    except:

        pass

    return "en"


# ============================================================
# TEXT TO SPEECH
# ============================================================

def speak_text(text, language):

    try:

        if language not in SUPPORTED_LANGUAGES:
            language = "en"

        tts = gTTS(
            text=text,
            lang=SUPPORTED_LANGUAGES[language]["voice"]
        )

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".mp3"
        ) as fp:

            filename = fp.name

        tts.save(filename)

        import threading
        import time

        def play_audio(file):
            try:
                playsound(file)
            except Exception:
                pass
            finally:
                time.sleep(0.5)
                if os.path.exists(file):
                    try:
                        os.remove(file)
                    except Exception:
                        pass

        threading.Thread(
            target=play_audio,
            args=(filename,),
            daemon=True
        ).start()

    except Exception as e:
        print("Speech Error:", e)
        # ============================================================
# VOICE INPUT
# ============================================================

def listen_voice():

    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.8

    try:
        with sr.Microphone() as source:

            print("Listening...")

            recognizer.adjust_for_ambient_noise(source, duration=1)

            audio = recognizer.listen(
                source,
                timeout=5,
                phrase_time_limit=10
            )

    except Exception as e:
        print("Microphone Error:", e)
        return ""

    for lang in ["ha", "en", "yo", "ig"]:

        try:

            text = recognizer.recognize_google(
                audio,
                language=SUPPORTED_LANGUAGES[lang]["speech"]
            )

            print(text)

            return text

        except:
            continue

    return ""


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are AgriAI.

You are an Agriculture Assistant developed for IITA (I-YOUTH).

Rules

1. Answer ONLY agriculture questions.

2. Agriculture includes

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

3. If a question is NOT agriculture related,
politely refuse.

4. Reply ONLY in the language used
by the user.

5. Keep answers practical,
simple and farmer friendly.

6. Never invent facts.
"""


# ============================================================
# GET AI RESPONSE
# ============================================================

def get_online_answer(user_input, language=None):

    global conversation_history

    try:

        conversation_history.append(
            {
                "role": "user",
                "text": user_input
            }
        )

        history = ""

        for item in conversation_history[-6:]:

            history += f"{item['role']}: {item['text']}\n"

        prompt = f"""
{SYSTEM_PROMPT}

Conversation

{history}

User

{user_input}
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        answer = response.text
           

    
        conversation_history.append(
            {
                "role": "assistant",
                "text": answer
            }
        )

        return answer

    except Exception as e:
        return f"AI Error:\n{e}"


