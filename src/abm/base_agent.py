"""
src/abm/base_agent.py

Common base class for all five pipeline agents. Wraps mesa.Agent and gives
each agent a typed handle to the shared Blackboard and the loaded config,
so individual agent modules (vision_agent, risk_agent, escalation_agent,
audit_agent — wired in here, implemented in their own packages) don't each
re-derive this plumbing.
"""
import mesa

from src.abm.blackboard import Blackboard


class BaseComplianceAgent(mesa.Agent):
    """Subclasses must implement step(). `self.model` is the
    ComplianceModel instance; `self.model.blackboard` is the current
    clip's shared state."""

    def __init__(self, unique_id: int, model: "mesa.Model", config: dict):
        super().__init__(unique_id, model)
        self.config = config

    @property
    def blackboard(self) -> Blackboard:
        return self.model.blackboard

    def step(self):
        raise NotImplementedError
