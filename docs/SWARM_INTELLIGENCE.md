# Swarm Intelligence Extensions (Research Section)

This system runs deterministically and lightly without any swarm
intelligence component — every threshold and weight in `config/config.yaml`
is a fixed, hand-set default. This document is a research extension
describing how Ant Colony Optimization (ACO) and Particle Swarm
Optimization (PSO) could be layered on top, as **optional offline tuning
scripts**, not runtime dependencies. None of the code below runs during
normal pipeline execution; it operates on logged run data to propose better
config values, which a human then reviews and applies.

This separation is itself a Green AI and reliability decision: a system
making real-time safety escalation decisions should not be self-modifying
its own thresholds live, against an unsupervised objective, in production.

---

## 1. Adaptive risk scoring (PSO)

**Problem.** `src/risk_agent/matrix.py` combines three signals — policy
callout level, personnel proximity, and recurrence count — with fixed,
hand-coded escalation rules (e.g., "personnel present always bumps the tier
by one"). The real trade-off between these signals is better expressed as
weights than as if/else rules, and the right weights are an empirical
question best answered against labeled data, not guessed.

**Formulation.** Define a continuous risk score:

```
risk_score = w1*confidence + w2*personnel_present + w3*recurrence_norm + w4*callout_weight
```

where `callout_weight` is 0 / 0.5 / 1.0 for None / WARNING / CRITICAL SAFETY
NOTICE, and `recurrence_norm` is recurrence count capped and normalized to
[0,1]. The four tier boundaries (LOW/MEDIUM/HIGH/CRITICAL) become three
threshold values `t1 < t2 < t3` on `risk_score`.

PSO searches `(w1, w2, w3, w4, t1, t2, t3)` — a 7-dimensional continuous
space — to minimize disagreement against a human-reviewed severity label
set (see `docs/EVALUATION.md` §3, "Severity matrix agreement").

```python
# src/research/pso_risk_tuning.py  (illustrative, NOT part of the runtime pipeline)
import numpy as np

def risk_score(features, params):
    w1, w2, w3, w4, *_ = params
    return (w1 * features["confidence"]
            + w2 * features["personnel_present"]
            + w3 * features["recurrence_norm"]
            + w4 * features["callout_weight"])

def tier_from_score(score, t1, t2, t3):
    if score < t1: return "LOW"
    if score < t2: return "MEDIUM"
    if score < t3: return "HIGH"
    return "CRITICAL"

def objective(params, labeled_examples):
    w1, w2, w3, w4, t1, t2, t3 = params
    errors = 0
    for features, human_tier in labeled_examples:
        predicted = tier_from_score(risk_score(features, params), t1, t2, t3)
        errors += (predicted != human_tier)
    return errors / len(labeled_examples)

def pso_optimize(labeled_examples, n_particles=30, n_iters=100, dim=7):
    positions = np.random.uniform(0, 1, (n_particles, dim))
    velocities = np.zeros((n_particles, dim))
    personal_best = positions.copy()
    personal_best_scores = np.array([objective(p, labeled_examples) for p in positions])
    global_best = personal_best[np.argmin(personal_best_scores)]

    w_inertia, c1, c2 = 0.6, 1.5, 1.5
    for _ in range(n_iters):
        r1, r2 = np.random.rand(n_particles, dim), np.random.rand(n_particles, dim)
        velocities = (w_inertia * velocities
                      + c1 * r1 * (personal_best - positions)
                      + c2 * r2 * (global_best - positions))
        positions = np.clip(positions + velocities, 0, 1)
        scores = np.array([objective(p, labeled_examples) for p in positions])
        improved = scores < personal_best_scores
        personal_best[improved] = positions[improved]
        personal_best_scores[improved] = scores[improved]
        global_best = personal_best[np.argmin(personal_best_scores)]
    return global_best  # -> write back into config.yaml's severity_matrix block
```

**Why PSO, not ACO, for this sub-problem:** the search space is continuous
(real-valued weights and thresholds) — PSO's natural domain. ACO is a
better fit for the discrete/combinatorial problems below.

---

## 2. Threshold optimization (PSO, vs. grid-search baseline)

**Problem.** `config.yaml`'s `vision_agent.uncertainty_margin` and the
per-class motion/color/edge thresholds hard-coded in
`src/vision_agent/detector.py` (e.g., the `0.015` off-walkway motion ratio,
`0.03` hi-vis ratio cutoff, `0.12` panel edge-density cutoff) were set by
inspection, not search. A precision/recall sweep over these is a
5-8 dimensional continuous optimization, with an F-beta objective.

```python
def detector_objective(thresholds, labeled_clips, beta=1.0):
    tp = fp = fn = 0
    for clip, ground_truth in labeled_clips:
        predictions = run_detector_with_thresholds(clip, thresholds)
        tp_c, fp_c, fn_c = match_against_ground_truth(predictions, ground_truth)
        tp += tp_c; fp += fp_c; fn += fn_c
    precision = tp / (tp + fp + 1e-9)
    recall = tp / (tp + fn + 1e-9)
    f_beta = (1 + beta**2) * precision * recall / (beta**2 * precision + recall + 1e-9)
    return -f_beta  # PSO minimizes; negate the score we want to maximize
```

A documented manual grid-search baseline should run alongside this in
`docs/EVALUATION.md` to demonstrate PSO's actual benefit over brute force:
for a 5-8 dimensional space, grid search at 5 points/dimension is
5^5 to 5^8 (3,125 to 390,625) evaluations, while PSO with 30 particles over
100 iterations is 3,000 evaluations — a meaningful reduction once each
evaluation costs a full pass over the labeled clip set.

---

## 3. Detector consensus (ACO)

**Problem.** If a second, independent lightweight detector were ensembled
alongside the classical-CV detector in `src/vision_agent/detector.py` —
e.g., a simple frame-differencing heuristic as a sanity check on the
background-subtraction approach — disagreements between detectors need a
combination rule. Voting weights here are a discrete/combinatorial
selection problem (which detector(s) to trust per behavior class, under a
constrained "total trust budget"), which fits ACO's pheromone-trail framing
better than PSO's continuous-position model.

```python
# Illustrative ACO-style consensus weighting.
def aco_consensus_search(behavior_classes, detectors, labeled_examples,
                          n_ants=20, n_iters=50, evaporation=0.1):
    pheromone = {bc: {d: 1.0 for d in detectors} for bc in behavior_classes}

    for _ in range(n_iters):
        ant_solutions = []
        for _ant in range(n_ants):
            allocation = {}
            for bc in behavior_classes:
                weights = pheromone[bc]
                total = sum(weights.values())
                probs = {d: w / total for d, w in weights.items()}
                allocation[bc] = max(probs, key=probs.get)
            score = evaluate_consensus_allocation(allocation, labeled_examples)
            ant_solutions.append((allocation, score))

        for bc in behavior_classes:
            for d in detectors:
                pheromone[bc][d] *= (1 - evaporation)
        for allocation, score in ant_solutions:
            for bc, chosen_detector in allocation.items():
                pheromone[bc][chosen_detector] += score

    return {bc: max(pheromone[bc], key=pheromone[bc].get) for bc in behavior_classes}
```

---

## 4. Resource-aware scheduling (ACO)

**Problem.** Under a fixed CPU compute budget (e.g., a deployment with N
camera zones but only enough headroom to run 4Hz high-frequency sampling
on a subset at once), deciding which zones get high- vs low-frequency
sampling is a constrained allocation problem — structurally similar to
ACO's classic resource-constrained job-allocation applications.

Each "ant" constructs a sampling-rate assignment across zones, respecting a
total-compute-budget constraint; pheromone reinforces assignments that
historically caught more true violations per unit compute spent — using
`RiskAssessmentAgent`'s existing `_recurrence` counters as the historical
violation-frequency signal per zone. This is the most speculative of the
four extensions and assumes a multi-camera deployment this implementation
doesn't yet model — included for completeness of the brief's
"resource-aware scheduling" prompt, not as a near-term build target.

---

## 5. Why none of this is wired into the runtime pipeline

1. **Reliability.** A safety-escalation system silently re-weighting its
   own severity thresholds during live operation, against an unsupervised
   or weakly-supervised objective, is a worse failure mode than a
   miscalibrated-but-stable fixed threshold — it would undermine the
   auditability the Audit Agent and `docs/ARCHITECTURE.md` are built
   around.
2. **Green AI.** PSO/ACO optimization runs are batch jobs over a labeled
   evaluation set, not per-clip inference — running them offline, on
   demand, keeps the always-on runtime footprint exactly as described in
   `docs/GREEN_AI.md`, with zero added per-clip compute.
3. **Requires labeled data this repository doesn't ship with.** All
   objective functions above need a human-reviewed ground-truth set
   (`docs/EVALUATION.md` §1-3) that doesn't exist until the system has
   been run and reviewed against real footage — this section documents
   the method, not a pre-computed result.
