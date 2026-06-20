# Evaluation

This document defines the methodology for evaluating the system once run
against real footage and a real policy document. The repository ships
with the evaluation *methodology and tooling approach*, not pre-computed
numbers — those depend on the specific clips, policy PDF, and human review
the system is deployed against.

## 1. Detection evaluation (Module 1)

**Method.** Sample a held-out subset of clips from `data/raw_clips/`
(recommend 15-20% of the dataset). For each clip, a human reviewer notes
the ground-truth violations present: behavior class, approximate timestamp,
and zone. Run `src.vision_agent.detector.detect_clip()` on the same clips
and match predictions to ground truth using a timestamp tolerance window
(recommend ±2 seconds, given the 4Hz sampling rate).

**Metrics, per behavior class and overall:**

| Metric | Definition |
|---|---|
| Precision | TP / (TP + FP) |
| Recall | TP / (TP + FN) |
| F1 | harmonic mean of precision/recall |
| Latency (mean, p95) | wall-clock seconds per clip through `detect_clip()` |

```python
# Illustrative scoring harness
def evaluate_detector(labeled_clips, config, tolerance_sec=2.0):
    results = {"TP": 0, "FP": 0, "FN": 0}
    for clip_path, ground_truth in labeled_clips:
        predictions = detect_clip(clip_path, config)
        matched_gt = set()
        for pred in predictions:
            match = next((
                gt for gt in ground_truth
                if gt["behavior_class"] == pred.behavior_class
                and abs(gt["timestamp_sec"] - pred.timestamp_sec) <= tolerance_sec
                and id(gt) not in matched_gt
            ), None)
            if match:
                results["TP"] += 1
                matched_gt.add(id(match))
            else:
                results["FP"] += 1
        results["FN"] += len(ground_truth) - len(matched_gt)
    precision = results["TP"] / (results["TP"] + results["FP"] + 1e-9)
    recall = results["TP"] / (results["TP"] + results["FN"] + 1e-9)
    return precision, recall
```

**Known limitation to document alongside results:** the classical-CV
detector (motion/color/edge heuristics — see `docs/GREEN_AI.md`) is
expected to perform unevenly across behavior classes. State-based
violations (electrical panel state) should show higher precision than
brief action-based violations (equipment intervention), since the latter
depends more on the 4Hz sampling rate catching the right frame. This
asymmetry should be reported per-class, not hidden behind an aggregate F1.

## 2. Policy grounding fidelity (RAG verification)

The assignment brief explicitly raises: *"If you use an LLM to parse the
policy, how will you verify that its extracted rules are faithful to the
source document?"* This system avoids that risk by construction — nothing
is generated, only retrieved (see `src/policy_agent/retriever.py`'s
docstring) — but retrieval can still surface the *wrong* passage. Evaluate
this directly:

**Method.** For a sample of ~30 detections (across all 4 behavior classes),
manually check whether the `policy_rule_ref` and `policy_supporting_text`
attached to the `DetectionRecord` actually support the classification made.
Report as a simple accuracy percentage: "N/30 retrieved citations correctly
support their associated detection."

**Failure modes to watch for, specifically:**
- Retrieval returns a chunk from the *wrong* behavior class (e.g.,
  forklift text retrieved for a pedestrian detection) — indicates the
  query phrasing in `get_observable_indicators()` needs refinement.
- Retrieval returns the right section but the *wrong* sentence within it
  (e.g., the safe-behavior description instead of the unsafe one) —
  indicates chunk boundaries in `chunker.py` may be splitting
  safe/unsafe contrast pairs apart; consider reducing `chunk_overlap_tokens`
  loss by increasing overlap.

## 3. Severity matrix agreement (Module 2)

**Method.** For the same sample of detections used in §2, have a human
reviewer (using the actual policy document) independently assign a
LOW/MEDIUM/HIGH/CRITICAL tier. Build a confusion matrix against
`src.risk_agent.matrix.classify_severity()`'s output.

```
                Human: LOW  MEDIUM  HIGH  CRITICAL
System: LOW       
System: MEDIUM    
System: HIGH      
System: CRITICAL  
```

Report exact-match accuracy and "within one tier" accuracy (since a
LOW-vs-MEDIUM disagreement is a much smaller error than a LOW-vs-CRITICAL
one). This confusion matrix is also the direct input to the PSO weight
search described in `docs/SWARM_INTELLIGENCE.md` §1.

## 4. System resource footprint (Green AI metrics)

Extends the qualitative analysis in `docs/GREEN_AI.md` with measured
numbers. No specialized power meter is assumed; energy is estimated from
CPU time, explicitly labeled as an estimate.

```python
import time, resource

def measure_stage(fn, *args, **kwargs):
    start_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    t0 = time.time()
    result = fn(*args, **kwargs)
    elapsed = time.time() - t0
    end_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Estimate, not measured hardware telemetry — see docs/GREEN_AI.md.
    estimated_watt_hours = (elapsed / 3600) * 12  # 12W assumed avg CPU package draw
    return result, {
        "elapsed_sec": elapsed,
        "peak_rss_mb": end_rss / 1024,
        "estimated_wh": estimated_watt_hours,
    }
```

Report per stage (Policy index build, per-clip detection, per-clip
retrieval, per-clip DB write) and as a full-batch total. Recommended
columns: `stage, mean_sec, p95_sec, peak_rss_mb, estimated_wh`.

## 5. End-to-end pipeline throughput

**Method.** Run `python3 -m src.abm.model` (or trigger `/api/pipeline/run`)
over the full clip set on a defined reference machine (document CPU model,
core count, RAM). Report clips/minute. This number, combined with §4's
per-clip resource estimate, supports a deployment sizing recommendation
(e.g., "one 4-core CPU instance can process clips from N camera feeds at
their native capture rate").

## 6. Reporting template

When these metrics are actually run, results should be written to
`outputs/reports/evaluation_summary.md` (or `.json`) with: dataset/policy
version used, date, reference hardware, and all tables above — kept
separate from this methodology document so the methodology stays stable
across re-runs.
