# ABM Design

## 1. Why Agent-Based Modeling for this problem

A compliance pipeline could be written as five plain function calls. The
case for modeling it as agents instead rests on three properties of the
real-world system being simulated/automated:

1. Each pipeline stage maps to a **distinct decision-maker with its own
   internal state and update rule** — the Policy Agent's vector index, the
   Vision Agent's per-clip frame buffer, the Risk Agent's running tally of
   recent severity tiers per zone (used for the "high-frequency recurrence"
   criterion in the CRITICAL tier definition).
2. The agents only communicate through **narrow, typed messages** (a
   `DetectionRecord`, a `(record, tier)` pair, etc.), matching the brief's
   explicit requirement that "outputs from one [module] feed into the next"
   via defined interface contracts.
3. Treating the pipeline as agents-in-an-environment, rather than a fixed
   call graph, is what makes Section 8 (swarm-intelligence extensions)
   possible without rewriting the core system: a PSO "threshold-tuning
   agent" or ACO "consensus-routing agent" can be added to the same Mesa
   model and read/write the same shared blackboard.

## 2. Framework choice: Mesa

[Mesa](https://mesa.readthedocs.io/) is a pure-Python ABM framework with no
GPU dependency and a small memory footprint (no spatial grid is required
for this problem, so the heaviest Mesa subsystems are unused). Alternatives
considered:

- **NetLogo** — would require a JVM bridge and is built around spatial grid
  visualization the project doesn't need; rejected on Green AI grounds
  (extra runtime, extra memory).
- **A hand-rolled agent loop** — possible, but Mesa's `Model`/`Agent`
  base classes and scheduler abstractions are already minimal, well-tested,
  and let us swap scheduling strategies (Section 4) with a one-line change,
  which is valuable for the Section 8 swarm-intelligence experiments.

## 3. Agents and their state

```python
class PolicyAgent(mesa.Agent):
    """Holds the FAISS index + chunk metadata. Stateless across clips
    (the policy document doesn't change during a run)."""
    def step(self): pass  # passive; only responds to retrieve() calls

class VisionAgent(mesa.Agent):
    """Holds per-clip frame buffer + detector model handle."""
    def step(self):
        self.model.blackboard["detections"] = self.detect(self.current_clip)

class RiskAssessmentAgent(mesa.Agent):
    """Holds a rolling per-zone severity history (last N tiers) used for
    the policy's 'high-frequency recurrence' CRITICAL criterion."""
    def step(self):
        detections = self.model.blackboard["detections"]
        self.model.blackboard["severities"] = [self.classify(d) for d in detections]

class EscalationAgent(mesa.Agent):
    def step(self):
        for record, tier in zip(self.model.blackboard["detections"],
                                  self.model.blackboard["severities"]):
            self.route(record, tier)

class AuditAgent(mesa.Agent):
    def step(self):
        self.write_reports(self.model.blackboard)
```

The `blackboard` is a plain dict on the `Model` instance — the simplest
possible shared environment, deliberately avoiding a message-queue or
pub/sub layer at the ABM level (the FastAPI layer added in Phase 6 owns the
*external* real-time pub/sub for the dashboard; internally, agents don't
need that overhead).

## 4. Scheduler: `RandomActivation`, one full chain per clip

```python
class ComplianceModel(mesa.Model):
    def __init__(self, clips, config):
        self.schedule = mesa.time.RandomActivation(self)
        self.blackboard = {}
        for agent_cls in [PolicyAgent, VisionAgent, RiskAssessmentAgent,
                           EscalationAgent, AuditAgent]:
            self.schedule.add(agent_cls(self.next_id(), self))

    def process_clip(self, clip):
        self.blackboard["clip"] = clip
        self.schedule.step()   # activates all 5 agents once, in shuffled order
```

**Why `RandomActivation` and not `SimultaneousActivation` or a `Grid`-based
scheduler:**

- The five agents have a strict *intra-clip* data dependency, which is
  enforced explicitly inside each agent's `step()` by reading the
  blackboard key the previous agent wrote — not by scheduler ordering. This
  means the scheduler itself doesn't need to guarantee order, and Mesa's
  lightest-weight scheduler is sufficient.
- `SimultaneousActivation` buffers all agents' state changes and applies
  them after every agent has computed its `advance()` step — useful when
  agents truly act concurrently on shared state (e.g., competing for a
  resource). That's not the case here and the extra buffering is pure
  overhead.
- A spatial `Grid` scheduler is for agents that occupy and move through
  physical space relative to each other (e.g., a factory-floor simulation
  with agents *as* forklifts). This system's agents represent pipeline
  *stages*, not physical entities, so a spatial grid would add memory and
  compute cost with no behavioral benefit. (Note: if a future iteration
  modeled each *camera zone* as a spatial agent — e.g., for the swarm-based
  resource-aware scheduling discussed in `SWARM_INTELLIGENCE.md` — a grid
  would become justified at that point.)
- Across the *batch* of clips, processing is naturally parallelizable
  (clip N doesn't depend on clip N-1's outcome), so the outer loop over
  clips is implemented as a plain Python loop calling `model.process_clip()`
  rather than something Mesa-scheduled — Mesa's scheduler models the
  *inter-agent* step structure within one clip, not the outer batch loop.

## 5. Termination & batch processing

One Mesa "step" = one clip fully processed by all five agents. The driver
script (`src/abm/run_pipeline.py`, added in Phase 4) iterates over all clips
in `data/raw_clips/`, calling `model.process_clip(clip)` once per clip, and
the model accumulates run-level statistics (total violations by class/tier,
per-zone recurrence counts) used both by the Risk Agent's CRITICAL-tier
recurrence rule and by the evaluation metrics in `docs/EVALUATION.md`.
