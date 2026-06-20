"""
src/abm/agents/risk_agent.py

Module 2 wiring: for each DetectionRecord on the blackboard, retrieves the
policy's severity callout language via the PolicyAgent, tracks per-zone
recurrence across the run, and applies src.risk_agent.matrix.classify_severity.
"""
from src.abm.base_agent import BaseComplianceAgent
from src.abm.blackboard import SeverityResult
from src.common.logging_utils import get_logger
from src.risk_agent.matrix import classify_severity

logger = get_logger(__name__)


class RiskAssessmentAgent(BaseComplianceAgent):
    def __init__(self, unique_id: int, model, config: dict, policy_agent):
        super().__init__(unique_id, model, config)
        self.policy_agent = policy_agent
        # zone -> behavior_class -> count, persists across the whole run
        # (the model instance, not the blackboard, which resets per clip).
        self._recurrence: dict[str, int] = {}

    def _recurrence_key(self, zone: str, behavior_class: str) -> str:
        return f"{zone}::{behavior_class}"

    def step(self):
        results: list[SeverityResult] = []

        for detection in self.blackboard.detections:
            try:
                signal = self.policy_agent.get_severity_signal(detection.behavior_label)
                callout_level = signal.callout_level
                section_ref = signal.supporting_section_ref
            except Exception as e:
                logger.warning(f"Severity signal retrieval failed for {detection.behavior_label}: {e}")
                callout_level = None
                section_ref = detection.policy_section_ref

            key = self._recurrence_key(detection.zone, detection.behavior_class)
            self._recurrence[key] = self._recurrence.get(key, 0) + 1
            recurrence_count = self._recurrence[key]

            tier, rationale = classify_severity(
                behavior_class=detection.behavior_class,
                confidence=detection.confidence,
                personnel_present=detection.personnel_present,
                recurrence_count=recurrence_count,
                callout_level=callout_level,
                config=self.config,
            )

            results.append(SeverityResult(
                detection=detection,
                tier=tier,
                rationale=rationale,
                policy_section_ref=section_ref,
            ))

        self.blackboard.severities = results
        logger.info(f"RiskAssessmentAgent: classified {len(results)} detection(s)")
