"""
src/abm/agents/audit_agent.py

Module 4 — Automated Report Generation. For every EscalationResult on the
blackboard, writes an immutable ComplianceReport row via
src.audit_agent.repository, with all fields required by the assignment
brief (event_id, timestamp, clip_id, zone, behavior_class,
policy_rule_ref, event_description, severity, escalation_action).
"""
from src.abm.base_agent import BaseComplianceAgent
from src.audit_agent.repository import write_report
from src.common.logging_utils import get_logger

logger = get_logger(__name__)


class AuditAgent(BaseComplianceAgent):
    def step(self):
        written = 0
        for escalation in self.blackboard.escalations:
            severity = escalation.severity
            detection = severity.detection
            try:
                write_report(
                    clip_id=detection.clip_id,
                    zone=detection.zone,
                    behavior_class=detection.behavior_class,
                    behavior_label=detection.behavior_label,
                    policy_rule_ref=severity.policy_section_ref,
                    event_description=detection.description,
                    severity=severity.tier,
                    escalation_action=escalation.action,
                    confidence=detection.confidence,
                    timestamp_sec_in_clip=detection.timestamp_sec,
                    config=self.config,
                )
                written += 1
            except Exception as e:
                logger.error(f"Failed to write compliance report for {detection.clip_id}: {e}")

        logger.info(f"AuditAgent: wrote {written} compliance report(s)")
