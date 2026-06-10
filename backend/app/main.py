"""FastAPI entrypoint for the RosterCopiilot mock MVP."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import changes, export, schedule

app = FastAPI(
    title="RosterCopiilot API",
    description="Mock MVP for NGO weekly roster scheduling, impact analysis, and human review.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(schedule.router)
app.include_router(changes.router)
app.include_router(export.router)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "mode": "mock",
        "service": "RosterCopiilot",
    }

