from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os

from online_agri_ai import get_online_answer
from disease_analyzer import analyze_crop_image

# ============================================================
# FastAPI
# ============================================================

app = FastAPI(
    title="AgriAI API",
    version="3.1.0"
)

# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Restrict later in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Upload Folder
# ============================================================

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ============================================================
# Models
# ============================================================

class ChatRequest(BaseModel):
    message: str


# ============================================================
# Home Endpoint
# ============================================================

@app.get("/")
def home():
    return {
        "status": "online",
        "service": "AgriAI API",
        "version": "3.1.0"
    }


# ============================================================
# Health Check
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# ============================================================
# AI Chat
# ============================================================

@app.post("/chat")
async def chat(request: ChatRequest):

    result = get_online_answer(request.message)

    return result


# ============================================================
# Disease Detection
# ============================================================

@app.post("/diagnose")
async def diagnose(file: UploadFile = File(...)):

    filepath = os.path.join(
        UPLOAD_FOLDER,
        file.filename
    )

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = analyze_crop_image(filepath)

    return result
