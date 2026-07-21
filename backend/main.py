"""
main.py — FastAPI application entry point.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import init_db
from routers import auth, documents, folders, clusters, search, rules


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure temp dir exists
    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    # Init DB tables + pgvector extension
    await init_db()
    yield


app = FastAPI(
    title="Smart Drive Filer API",
    version="1.0.0",
    description="AI-powered Google Drive document organizer",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(folders.router, prefix="/folders", tags=["folders"])
app.include_router(clusters.router, prefix="/clusters", tags=["clusters"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(rules.router, prefix="/rules", tags=["rules"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "smart-drive-filer"}
