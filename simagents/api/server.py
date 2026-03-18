"""FastAPI application for SimAgents GUI."""
from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from simagents.api.session import session_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    session_manager.cleanup()


app = FastAPI(title="SimAgents API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from simagents.api.routes import upload
app.include_router(upload.router)
from simagents.api.routes import settings_routes, parameters
app.include_router(settings_routes.router)
app.include_router(parameters.router)
