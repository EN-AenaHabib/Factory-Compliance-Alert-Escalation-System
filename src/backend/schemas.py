"""
src/backend/schemas.py
Pydantic models for API request/response shapes.
"""
from pydantic import BaseModel


class ComplianceReportOut(BaseModel):
    event_id: str
    timestamp: str
    clip_id: str
    zone: str
    behavior_class: str
    behavior_label: str
    policy_rule_ref: str
    event_description: str
    severity: str
    escalation_action: str
    confidence: float | None = None
    timestamp_sec_in_clip: float | None = None


class RunStatsOut(BaseModel):
    clips_processed: int
    detections_by_class: dict
    severities_by_tier: dict


class PipelineRunResponse(BaseModel):
    status: str
    clips_processed: int
    stats: RunStatsOut
