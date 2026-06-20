"""
src/abm/agents/vision_agent.py

Module 1 — Detection Engine. Runs the lightweight CV detector
(src/vision_agent/detector.py) over the current clip, then grounds each
raw detection in the compliance policy by querying the PolicyAgent for the
relevant observable-indicator passage, producing a fully-cited
DetectionRecord on the shared Blackboard.
"""
import uuid

from src.abm.base_agent import BaseComplianceAgent
from src.abm.blackboard import DetectionRecord
from src.common.logging_utils import get_logger
from src.vision_agent.detector import detect_clip

logger = get_logger(__name__)

BEHAVIOR_LABELS = {
    "pedestrian_movement": "Pedestrian Walkway Violation",
    "equipment_intervention": "Unsafe Equipment Intervention",
    "electrical_panel_management": "Electrical Panel Violation",
    "forklift_load_management": "Forklift Overload Violation",
}


class VisionAgent(BaseComplianceAgent):
    def __init__(self, unique_id: int, model, config: dict, policy_agent):
        super().__init__(unique_id, model, config)
        self.policy_agent = policy_agent

    def step(self):
        clip_path = self.blackboard.clip_path
        clip_id = self.blackboard.clip_id
        if not clip_path:
            self.blackboard.detections = []
            return

        try:
            raw_detections = detect_clip(clip_path, self.config)
        except Exception as e:
            logger.error(f"Vision detection failed for {clip_id}: {e}")
            self.blackboard.detections = []
            return

        records: list[DetectionRecord] = []
        for raw in raw_detections:
            label = BEHAVIOR_LABELS.get(raw.behavior_class, raw.behavior_class)

            # Ground the detection in the policy text — required by the
            # "observable indicators must be traceable to the relevant
            # policy section" requirement.
            try:
                indicator_chunks = self.policy_agent.get_observable_indicators(label, k=1)
            except Exception as e:
                logger.warning(f"Policy grounding failed for {label}: {e}")
                indicator_chunks = []

            if indicator_chunks:
                section_ref = indicator_chunks[0].section_ref
                supporting_text = indicator_chunks[0].text
            else:
                section_ref = "Unresolved"
                supporting_text = ""

            records.append(DetectionRecord(
                clip_id=clip_id,
                timestamp_sec=raw.timestamp_sec,
                behavior_class=raw.behavior_class,
                behavior_label=label,
                description=raw.description,
                zone=raw.zone,
                confidence=raw.confidence,
                personnel_present=raw.personnel_present,
                policy_section_ref=section_ref,
                policy_supporting_text=supporting_text,
            ))

        self.blackboard.detections = records
        logger.info(f"VisionAgent: {len(records)} grounded detection(s) for {clip_id}")
