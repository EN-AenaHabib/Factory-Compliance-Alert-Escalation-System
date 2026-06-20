"""
src/abm/agents/policy_agent.py

The Policy Agent in ABM terms: it holds no per-clip state (the policy
document doesn't change during a run) and is passive in the schedule — it
doesn't write to the blackboard itself, it answers retrieve() calls made by
the Vision and Risk agents during their own step(). This mirrors
docs/ABM_DESIGN.md's description of PolicyAgent.step() as a no-op.
"""
from src.abm.base_agent import BaseComplianceAgent
from src.policy_agent.retriever import PolicyRetriever, get_retriever
from src.policy_agent.rule_reasoner import (
    SeveritySignal,
    get_observable_indicators,
    get_severity_signal,
)


class PolicyAgent(BaseComplianceAgent):
    def __init__(self, unique_id: int, model, config: dict):
        super().__init__(unique_id, model, config)
        self.retriever: PolicyRetriever = get_retriever(config)

    def step(self):
        # Passive: the policy index is static for the whole run, so there
        # is nothing to update per clip. Present in the schedule for
        # architectural symmetry and so a future swarm-tuning extension
        # (docs/SWARM_INTELLIGENCE.md) has a natural place to plug in
        # adaptive retrieval-weight updates without restructuring agents.
        pass

    def retrieve_for_behavior_class(self, behavior_label: str, aspect: str, k: int = 4):
        return self.retriever.retrieve_for_behavior_class(behavior_label, aspect=aspect, k=k)

    def get_severity_signal(self, behavior_label: str) -> SeveritySignal:
        return get_severity_signal(behavior_label, retriever=self.retriever)

    def get_observable_indicators(self, behavior_label: str, k: int = 3):
        return get_observable_indicators(behavior_label, retriever=self.retriever, k=k)
