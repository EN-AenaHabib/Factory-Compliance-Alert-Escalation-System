"""
src/backend/routes_pipeline.py

Endpoint to (re)run the ABM batch pipeline over whatever clips are in
data/raw_clips/. The dashboard's Live Feed Monitor (View A) calls this to
simulate "live" processing — clips are processed in order and each
HIGH/CRITICAL event streams out over /api/stream/alerts as it's produced
(EscalationAgent publishes synchronously during the run, so SSE subscribers
see events as the batch progresses, not only after it finishes).
"""
from fastapi import APIRouter

from src.abm.model import run_batch
from src.backend.schemas import PipelineRunResponse, RunStatsOut
from src.common.logging_utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/run", response_model=PipelineRunResponse)
def run_pipeline():
    model = run_batch()
    return PipelineRunResponse(
        status="completed",
        clips_processed=model.run_stats["clips_processed"],
        stats=RunStatsOut(**model.run_stats),
    )
