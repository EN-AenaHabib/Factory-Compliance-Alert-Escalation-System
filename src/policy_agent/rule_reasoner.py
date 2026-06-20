"""
src/policy_agent/rule_reasoner.py

Sits on top of PolicyRetriever and answers the specific structured
questions the Risk Assessment Agent and Vision Agent need, e.g.:
"what observable indicators define this behavior as unsafe?" and
"is this behavior flagged WARNING or CRITICAL SAFETY NOTICE in the policy?"

Still purely retrieval-based — no text is generated, only retrieved and
pattern-matched, keeping the system's policy-grounding fully auditable
(every signal returned here carries the section_ref it came from).
"""
from dataclasses import dataclass

from src.policy_agent.retriever import PolicyRetriever, RetrievedChunk, get_retriever


@dataclass
class SeveritySignal:
    behavior_label: str
    callout_level: str | None      # "WARNING", "CRITICAL SAFETY NOTICE", or None
    supporting_section_ref: str
    supporting_text: str
    score: float


def get_severity_signal(
    behavior_label: str, retriever: PolicyRetriever | None = None
) -> SeveritySignal:
    retriever = retriever or get_retriever()
    chunks = retriever.retrieve_for_behavior_class(
        behavior_label, aspect="severity hazard WARNING CRITICAL SAFETY NOTICE", k=3
    )

    if not chunks:
        return SeveritySignal(
            behavior_label=behavior_label,
            callout_level=None,
            supporting_section_ref="N/A",
            supporting_text="",
            score=0.0,
        )

    # Prefer the highest-scoring chunk that actually carries a callout;
    # fall back to the top chunk overall if none do.
    callout_chunks = [c for c in chunks if c.callout]
    best = callout_chunks[0] if callout_chunks else chunks[0]

    return SeveritySignal(
        behavior_label=behavior_label,
        callout_level=best.callout,
        supporting_section_ref=best.section_ref,
        supporting_text=best.text,
        score=best.score,
    )


def get_observable_indicators(
    behavior_label: str, retriever: PolicyRetriever | None = None, k: int = 3
) -> list[RetrievedChunk]:
    """Returns the policy passages most likely to describe the observable
    visual indicators (vest color, block count, panel state, walkway
    position, etc.) for a given behavior class — used by the Vision Agent
    to ground its detection logic in policy text rather than hard-coded
    class names."""
    retriever = retriever or get_retriever()
    return retriever.retrieve_for_behavior_class(
        behavior_label, aspect="observable indicator visual sign", k=k
    )
