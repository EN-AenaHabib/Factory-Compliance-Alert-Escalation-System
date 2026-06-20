"""
src/abm/blackboard.py

The Blackboard is the shared environment state Mesa agents read/write to
within one model.process_clip() call. Deliberately a plain dataclass, not a
message queue — see docs/ABM_DESIGN.md section 4 for why that's the right
amount of machinery for in-process agent communication (the real-time
pub/sub layer for the dashboard lives in the backend, not here).
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DetectionRecord:
    clip_id: str
    timestamp_sec: float
    behavior_class: str          # one of the 4 policy-defined classes (config.yaml id)
    behavior_label: str
    description: str
    zone: str
    confidence: float
    personnel_present: bool
    policy_section_ref: str
    policy_supporting_text: str


@dataclass
class SeverityResult:
    detection: DetectionRecord
    tier: str                     # LOW / MEDIUM / HIGH / CRITICAL
    rationale: str
    policy_section_ref: str


@dataclass
class EscalationResult:
    severity: SeverityResult
    action: str                   # e.g. "Logged to DB" / "Real-time alert triggered + DB log"
    alerted: bool


@dataclass
class Blackboard:
    clip_id: str = ""
    clip_path: str = ""
    detections: list[DetectionRecord] = field(default_factory=list)
    severities: list[SeverityResult] = field(default_factory=list)
    escalations: list[EscalationResult] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def reset_for_clip(self, clip_id: str, clip_path: str):
        self.clip_id = clip_id
        self.clip_path = clip_path
        self.detections = []
        self.severities = []
        self.escalations = []
        self.extra = {}
