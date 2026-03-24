"""FastAPI application for SimAgents GUI."""
from __future__ import annotations
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from simagents.api.session import session_manager

# Load .env from project root (ensures API keys are available)
_project_root = Path(__file__).resolve().parents[2]
load_dotenv(_project_root / ".env")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    session_manager.cleanup()


app = FastAPI(title="SimAgents API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from simagents.api.routes import upload
app.include_router(upload.router)
from simagents.api.routes import settings_routes, parameters, profiles
app.include_router(settings_routes.router)
app.include_router(parameters.router)
app.include_router(profiles.router)
from simagents.api.routes import extract
app.include_router(extract.router)
