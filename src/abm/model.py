"""
src/abm/model.py
"""
import mesa

from src.abm.agents.audit_agent import AuditAgent
from src.abm.agents.escalation_agent import EscalationAgent
from src.abm.agents.policy_agent import PolicyAgent
from src.abm.agents.risk_agent import RiskAssessmentAgent
from src.abm.agents.vision_agent import VisionAgent
from src.abm.blackboard import Blackboard
from src.common.config import load_config, resolve_path
from src.common.logging_utils import get_logger

logger = get_logger(__name__)

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}


class ComplianceModel(mesa.Model):
    def __init__(self, config: dict | None = None):
        super().__init__()
        self.config = config or load_config()
        self.random.seed(self.config["abm"]["random_seed"])

        self.schedule = mesa.time.RandomActivation(self)
        self.blackboard = Blackboard()

        self.run_stats = {
            "clips_processed": 0,
            "detections_by_class": {},
            "severities_by_tier": {},
        }

        self._build_agents()

    def _build_agents(self):
        policy_agent = PolicyAgent(self.next_id(), self, self.config)
        vision_agent = VisionAgent(self.next_id(), self, self.config, policy_agent)
        risk_agent = RiskAssessmentAgent(self.next_id(), self, self.config, policy_agent)
        escalation_agent = EscalationAgent(self.next_id(), self, self.config)
        audit_agent = AuditAgent(self.next_id(), self, self.config)

        for agent in [policy_agent, vision_agent, risk_agent, escalation_agent, audit_agent]:
            self.schedule.add(agent)

        # Strict ordered list — guarantees Policy->Vision->Risk->Escalation->Audit
        # RandomActivation shuffles randomly which broke AuditAgent reading
        # empty blackboard.escalations before EscalationAgent populated it.
        self._ordered_agents = [
            policy_agent,
            vision_agent,
            risk_agent,
            escalation_agent,
            audit_agent,
        ]

        self.agents_by_role = {
            "policy": policy_agent,
            "vision": vision_agent,
            "risk": risk_agent,
            "escalation": escalation_agent,
            "audit": audit_agent,
        }

    def process_clip(self, clip_id: str, clip_path: str) -> Blackboard:
        self.blackboard.reset_for_clip(clip_id, clip_path)
        # Execute in strict order instead of schedule.step()
        # This guarantees Vision writes detections BEFORE Risk reads them,
        # and Escalation writes escalations BEFORE Audit reads them.
        for agent in self._ordered_agents:
            agent.step()
        self._update_run_stats()
        self.run_stats["clips_processed"] += 1
        return self.blackboard

    def _update_run_stats(self):
        for d in self.blackboard.detections:
            self.run_stats["detections_by_class"][d.behavior_class] = (
                self.run_stats["detections_by_class"].get(d.behavior_class, 0) + 1
            )
        for s in self.blackboard.severities:
            self.run_stats["severities_by_tier"][s.tier] = (
                self.run_stats["severities_by_tier"].get(s.tier, 0) + 1
            )


def discover_clips(config: dict) -> list[tuple[str, str]]:
    raw_clips_dir = resolve_path(config["paths"]["raw_clips_dir"])
    clips = sorted(
        p for p in raw_clips_dir.rglob("*") if p.suffix.lower() in VIDEO_EXTENSIONS
    )
    return [(p.name, str(p)) for p in clips]


def run_batch(config: dict | None = None) -> ComplianceModel:
    cfg = config or load_config()
    model = ComplianceModel(cfg)
    clips = discover_clips(cfg)

    if not clips:
        logger.warning(
            "No clips found in data/raw_clips/. Run scripts/download_dataset.py "
            "or place clips there manually."
        )
        return model

    logger.info(f"Processing {len(clips)} clip(s) through the ABM pipeline...")
    for clip_id, clip_path in clips:
        model.process_clip(clip_id, clip_path)

    logger.info(f"Run complete. Stats: {model.run_stats}")
    return model


if __name__ == "__main__":
    run_batch()
