"""
src/abm/agents/escalation_agent.py

Module 3 — Escalation Pipeline. Mandatory routing rules:
  LOW / MEDIUM   -> DB log only
  HIGH / CRITICAL -> DB log + real-time alert (pushed onto the EventBus,
                      consumed by the FastAPI SSE endpoint)
"""
import uuid

from src.abm.base_agent import BaseComplianceAgent
from src.abm.blackboard import EscalationResult
from src.common.logging_utils import get_logger
from src.escalation_agent.event_bus import AlertEvent, event_bus, now_iso

logger = get_logger(__name__)


class EscalationAgent(BaseComplianceAgent):
    def step(self):
        escalation_cfg = self.config["escalation"]
        alert_tiers = set(escalation_cfg.get("alert_tiers", ["HIGH", "CRITICAL"]))

        results: list[EscalationResult] = []
        for severity in self.blackboard.severities:
            alerted = severity.tier in alert_tiers

            if alerted:
                action = "Real-time alert triggered + DB log"
                event = AlertEvent(
                    event_id=str(uuid.uuid4()),
                    timestamp=now_iso(),
                    clip_id=severity.detection.clip_id,
                    zone=severity.detection.zone,
                    behavior_class=severity.detection.behavior_class,
                    behavior_label=severity.detection.behavior_label,
                    severity=severity.tier,
                    description=severity.detection.description,
                    policy_section_ref=severity.policy_section_ref,
                )
                try:
                    event_bus.publish(event)
                except Exception as e:
                    logger.warning(f"Failed to publish real-time alert: {e}")
            else:
                action = "Logged to DB"

            results.append(EscalationResult(
                severity=severity,
                action=action,
                alerted=alerted,
            ))

        self.blackboard.escalations = results
        logger.info(
            f"EscalationAgent: {len(results)} event(s) routed "
            f"({sum(1 for r in results if r.alerted)} real-time alert(s))"
        )
