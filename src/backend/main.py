"""
src/backend/main.py

FastAPI entry point. Run via:
    uvicorn src.backend.main:app --host 0.0.0.0 --port 8000

or scripts/run_backend.sh.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.audit_agent.db import init_db
from src.backend.routes_pipeline import router as pipeline_router
from src.backend.routes_reports import router as reports_router
from src.backend.routes_stream import router as stream_router
from src.common.config import load_config
from src.common.logging_utils import get_logger

logger = get_logger(__name__)

cfg = load_config()
app = FastAPI(
    title="Factory Compliance & Alert Escalation System",
    description="Offline, agent-based factory safety compliance API.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg["backend"].get("cors_allow_origins", ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports_router)
app.include_router(stream_router)
app.include_router(pipeline_router)


@app.on_event("startup")
def on_startup():
    init_db(cfg)
    logger.info("Backend started. Audit DB initialized.")


@app.get("/api/health")
def health():
    return {"status": "ok"}
