"""
src/risk_agent/matrix.py

Module 2 — Severity Categorization Matrix. Pure logic, independently
testable from the ABM wiring.

Tier assignment combines three signals, all required by the assignment
brief and docs/ABM_DESIGN.md:
  1. The policy's own callout language for this behavior class (WARNING vs
     CRITICAL SAFETY NOTICE), retrieved by the PolicyAgent.
  2. Personnel proximity (config["severity_matrix"]["personnel_proximity_escalation"]).
  3. Recurrence — repeated detections of the same behavior_class in the
     same zone within a run bump the tier, per the brief's "high-frequency
     recurrence" CRITICAL criterion.
"""
TIER_ORDER = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def _bump(tier: str, steps: int = 1) -> str:
    idx = TIER_ORDER.index(tier)
    return TIER_ORDER[min(idx + steps, len(TIER_ORDER) - 1)]


def classify_severity(
    behavior_class: str,
    confidence: float,
    personnel_present: bool,
    recurrence_count: int,
    callout_level: str | None,
    config: dict,
) -> tuple[str, str]:
    """
    Returns (tier, rationale_text).
    """
    sm_cfg = config["severity_matrix"]
    base_tier = sm_cfg["default_tier_by_class"].get(behavior_class, "MEDIUM")
    rationale_parts = [f"Base tier for '{behavior_class}' per policy default: {base_tier}."]

    tier = base_tier

    # Policy callout language overrides/reinforces the base tier.
    if callout_level == "CRITICAL SAFETY NOTICE":
        tier = "CRITICAL"
        rationale_parts.append("Policy text carries a CRITICAL SAFETY NOTICE callout for this behavior.")
    elif callout_level == "WARNING" and tier == "LOW":
        tier = "MEDIUM"
        rationale_parts.append("Policy text carries a WARNING callout; tier raised from LOW to MEDIUM.")

    # Low-confidence / borderline detections are not auto-escalated to
    # CRITICAL — per the assignment's own guidance ("if your detector is
    # uncertain about a borderline case... how should your system handle
    # that?"), borderline cases are capped at MEDIUM unless the policy
    # explicitly flags the class as CRITICAL.
    uncertainty_margin = config.get("vision_agent", {}).get("uncertainty_margin", 0.15)
    if confidence < (0.5 + uncertainty_margin) and tier not in ("LOW",):
        if callout_level != "CRITICAL SAFETY NOTICE":
            tier = min(tier, "MEDIUM", key=TIER_ORDER.index)
            rationale_parts.append(
                f"Detection confidence ({confidence:.2f}) within the uncertainty band; "
                f"tier capped at MEDIUM pending higher-confidence confirmation."
            )

    # Personnel proximity escalation.
    if personnel_present and sm_cfg.get("personnel_proximity_escalation", True):
        new_tier = _bump(tier, 1)
        if new_tier != tier:
            rationale_parts.append(f"Personnel present in-frame; tier escalated {tier} -> {new_tier}.")
        tier = new_tier

    # Recurrence escalation — repeated violations of the same class/zone.
    if recurrence_count >= 3:
        new_tier = "CRITICAL"
        if new_tier != tier:
            rationale_parts.append(
                f"High-frequency recurrence ({recurrence_count} occurrences this run); tier escalated to CRITICAL."
            )
        tier = new_tier
    elif recurrence_count == 2:
        new_tier = _bump(tier, 1)
        if new_tier != tier:
            rationale_parts.append(f"Repeat occurrence (#{recurrence_count}); tier escalated {tier} -> {new_tier}.")
        tier = new_tier

    return tier, " ".join(rationale_parts)
