# Green AI Analysis

Green AI, as framed by Schwartz et al. (2020), asks that efficiency
(compute, memory, energy, and the resulting carbon/cost footprint) be
reported and optimized for as a first-class metric alongside accuracy. This
document justifies every model and infrastructure choice in the system
against that standard.

## 1. Component-by-component justification

| Component | Choice | Alternative considered | Why this is the greener choice |
|---|---|---|---|
| Policy embeddings | `all-MiniLM-L6-v2` (22M params, ~80MB) | `text-embedding-3-large` / hosted API | Runs a full policy-document embedding pass (a few hundred chunks) in well under a second on a laptop CPU; no network round-trip energy cost, no data leaves the machine |
| Vector index | FAISS `IndexFlatIP`, exact search | An approximate index (HNSW/IVF) or a hosted vector DB | The policy document indexes to only a few hundred chunks — exact search is *faster and lighter* than building/maintaining an approximate index at this scale; a hosted vector DB would add a persistent server process and network calls for no accuracy benefit |
| Video frame sampling | 4 Hz sampling + downscale to 640×360 before inference | Full-resolution, full-framerate inference | At 1080p/25fps, full inference processes ~9x more pixels per frame and ~6x more frames per second than necessary for clips of 3-18s; sampling cuts inference compute by roughly an order of magnitude with negligible loss for the state-based and short-action behaviors in this dataset |
| Detector backend | ONNX Runtime CPU, compact mobile-class architecture | A large vision-language model (zero-shot VLM) | A VLM gives flexible zero-shot classes but costs orders of magnitude more FLOPs per frame and typically wants GPU acceleration to run at usable latency; a compact CPU detector matches this task's fixed, small (4-class) label set |
| Policy rule reasoning | Retrieval (FAISS) + rule-based scoring, no generative step | LLM-based rule extraction at inference time | Removes a per-query LLM call entirely — retrieval is a single forward pass through a 22M-parameter encoder versus billions of parameters in a generative model |
| ABM framework | Mesa (pure Python, no GPU, no spatial grid used) | NetLogo (JVM), custom distributed agent framework | No second runtime (JVM) to keep resident, no distributed-systems overhead (message brokers, service discovery) for a workload that fits on one machine |
| Backend | FastAPI + Uvicorn | A heavier ASGI stack, or a Node.js microservice mesh | Single lightweight process; async I/O lets the same process handle the SSE stream and REST API without spinning up additional workers for typical demo-scale concurrency |
| Real-time alerts | In-process SSE (`sse-starlette`) | A managed message broker (Kafka, managed pub/sub) | No second always-on service to run; SSE over the existing HTTP connection is enough for the alert volumes this system produces |
| Database | SQLite | PostgreSQL / managed cloud DB | No separate database server process running 24/7; SQLite is sufficient for the audit-log write/read pattern (mostly appends, occasional filtered reads) at this data volume |
| Dataset/library hosting | Local files after one-time Kaggle download | Streaming from cloud storage per request | Clips are processed once per run from local disk; no repeated network transfer cost |

## 2. Where compute is deliberately *not* minimized further

Two choices favor correctness/auditability over the absolute minimum
compute, and that trade-off is stated explicitly rather than hidden:

- **Exact (not approximate) vector search.** Approximate search would save
  a small amount of CPU at index-build time, but at this corpus size (one
  policy document) the absolute savings are negligible while the risk of
  silently missing the correct policy section for a severity decision is
  not — and policy grounding accuracy is a hard requirement of the brief.
- **4 Hz frame sampling rather than 1-2 Hz.** A lower rate would cut
  inference compute further but risks missing brief action-based violations
  (e.g., a momentary unsafe equipment intervention); 4 Hz was chosen as the
  documented compute/recall trade-off point — see `docs/EVALUATION.md`
  (Phase 8) for the empirical comparison once detection metrics are added.

## 3. Measuring footprint (Phase 8 deliverable)

`docs/EVALUATION.md` will report, per pipeline stage: wall-clock time per
clip, peak RSS memory, and an estimated energy figure derived from CPU
time × a documented average CPU package power draw (no specialized power
meter is assumed — the estimate is explicitly labeled as such, not measured
hardware telemetry).
