from fastapi import UploadFile, File
import shutil
import os

from disease_analyzer import analyze_crop_image
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from online_agri_ai import (
    get_online_answer,
    detect_language
)

app = FastAPI(
    title="AgriAI API",
    version="1.0.0"
)
UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Allow Flutter to communicate with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # We'll restrict this later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    language: str


@app.get("/")
def home():
    return {
        "message": "Welcome to AgriAI API"
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    language = detect_language(request.message)

    answer = get_online_answer(
        request.message,
        language
    )

    return ChatResponse(
        reply=answer,
        language=language
    )
@app.post("/analyze-image")
async def analyze_image(file: UploadFile = File(...)):

    # Save uploaded image
    image_path = os.path.join(
        UPLOAD_FOLDER,
        file.filename,
    )

    with open(image_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # Analyze with Gemini Vision
        result = analyze_crop_image(image_path)
        return result

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

    finally:
        # Delete uploaded image
        if os.path.exists(image_path):
            os.remove(image_path)