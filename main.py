from fastapi import Depends
from fastapi import Form
from sqlalchemy.orm import Session
from fastapi.staticfiles import StaticFiles
import crud
import schemas
import models
from routers.marketplace import router as marketplace_router

from database import get_db

from database import engine
from models import Base

Base.metadata.create_all(bind=engine)

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os
from routers.auth import router as auth_router
from online_agri_ai import get_online_answer
from disease_analyzer import analyze_crop_image
from routers.admin import router as admin_router

# ============================================================
# FastAPI
# ============================================================

app = FastAPI(
    title="AgriAI API",
    version="3.1.0"
)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
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


# ============================================================
# REGISTER ROUTERS
# ============================================================

app.include_router(
    marketplace_router
)

app.include_router(
    auth_router
)

app.include_router(
    admin_router
)