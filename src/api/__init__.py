"""API module for FastAPI endpoints."""

from fastapi import FastAPI
from src.api.routes import router

app = FastAPI(
    title="Data Agent API",
    description="Agente de análisis de datos con Python/Pandas/ML",
    version="1.0.0"
)

app.include_router(router)

__all__ = ["app", "router"]
