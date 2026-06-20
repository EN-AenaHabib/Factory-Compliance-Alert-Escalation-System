# Factory Compliance & Alert Escalation System

A fully offline, agent-based factory safety compliance pipeline: it parses a
regulatory PDF, detects unsafe behavior in factory video, reasons about risk
severity, escalates real-time alerts, and produces an immutable audit trail —
all on CPU, with zero calls to any external API, LLM service, or cloud
platform.

> **Build status:** this repository is being assembled in phases. See
> [Project status](#project-status) below for what is implemented so far.

---

## 1. Why this design

The original assignment allows any architecture. This implementation
deliberately constrains itself further, for research and deployability
reasons:

- **No external LLM/API calls.** Policy rule extraction uses a fully local
  Retrieval-Augmented Generation (RAG) pipeline (PDF parse → chunk → local
  sentence-embedding → FAISS vector index → retrieval), not a hosted LLM.
- **No heavy GPU models.** Detection uses frame-sampling + a compact
  ONNX/classical-CV pipeline that runs on CPU in real time on the
  resolution-reduced frames.
- **Agent-Based Modeling (ABM)**, not a monolithic script: a Policy Agent,
  Vision Agent, Risk Assessment Agent, Escalation Agent, and Audit Agent
  each own one pipeline stage and communicate through a shared model state.
  See [`docs/ABM_DESIGN.md`](docs/ABM_DESIGN.md).
- **Green AI throughout.** Every model/library choice is justified against
  compute, memory, and energy cost in [`docs/GREEN_AI.md`](docs/GREEN_AI.md).
- **Swarm intelligence as a research extension**, not a hard dependency —
  [`docs/SWARM_INTELLIGENCE.md`](docs/SWARM_INTELLIGENCE.md) discusses how
  ACO/PSO could adaptively tune severity thresholds, detector consensus
  weights, and scheduling, without requiring them for the system to run.

Full system diagrams and the inter-agent data flow are in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## 2. Project status

| Component | Status |
|---|---|
| Repo scaffold, config, Docker, deployment scripts, architecture docs | ✅ Done |
| Policy Agent — offline RAG pipeline (PDF parse → chunk → embed → FAISS → retrieve) | ✅ Done |
| Kaggle dataset auto-download (`scripts/download_dataset.py`) | ✅ Done |
| ABM core (Mesa model, scheduler, blackboard, base agent) | ✅ Done |
| Vision Agent — classical CV frame sampling + zone-based detection (Module 1) | ✅ Done |
| Risk Assessment Agent — severity matrix, policy callouts, recurrence, proximity (Module 2) | ✅ Done |
| Escalation Agent — DB/alert routing + in-process SSE event bus (Module 3) | ✅ Done |
| Audit Agent — SQLite schema + immutable report writing (Module 4) | ✅ Done |
| FastAPI backend — REST + SSE real-time alert stream | ✅ Done |
| React dashboard — Live Feed / Alert Timeline / Historical Log + export (Module 5) | ✅ Done |
| Swarm intelligence research (PSO/ACO extensions) | ✅ Done |
| Green AI + evaluation methodology | ✅ Done |

> The Vision Agent uses a classical, CPU-only computer-vision detector
> (motion + color + edge heuristics per zone), not a trained deep model —
> a deliberate Green AI choice. Swapping in a trained ONNX model later only
> requires changing `src/vision_agent/detector.py`'s internals; the
> `VisionAgent` wrapper's interface is unaffected.

## 3. Running the full system

```bash
# 1. One-time setup (venv, deps, dataset, vector store, DB)
bash scripts/setup.sh

# 2. Start the backend (FastAPI + SSE)
bash scripts/run_backend.sh
# -> http://localhost:8000  (check http://localhost:8000/api/health)

# 3. Start the dashboard
bash scripts/run_dashboard.sh
# -> http://localhost:5173
```

In the dashboard, click **Run Pipeline** — it processes every clip in
`data/raw_clips/` through Policy → Vision → Risk → Escalation → Audit.
HIGH/CRITICAL events appear instantly (SSE push) in the Live Feed and
Alert Timeline views; every event (any tier) is written to SQLite and
viewable/exportable from the Historical Log view.

Or run the pipeline headlessly:

```bash
python3 -m src.abm.model
```

A ready-to-run Google Colab notebook that clones this repo and exercises
the offline RAG pipeline + ABM core end-to-end is at
[`notebooks/Factory_Compliance_System_Test.ipynb`](notebooks/Factory_Compliance_System_Test.ipynb).

## 3. One-command setup

```bash
git clone <this-repo>
cd factory-compliance-system
cp .env.example .env          # then fill in KAGGLE_USERNAME / KAGGLE_KEY
bash scripts/setup.sh
```

`setup.sh` creates a virtual environment, installs all dependencies,
downloads the Kaggle video dataset (the **only** manual input required is a
Kaggle API token — Kaggle mandates this for any programmatic access; no
client library can bypass it), builds the offline policy vector store from
whatever PDF is placed at `data/policy/compliance_policy.pdf`, and
initializes the SQLite audit database.

Run with Docker instead, if preferred:

```bash
docker-compose up --build
```

Once setup finishes:

```bash
bash scripts/run_backend.sh     # FastAPI on :8000
bash scripts/run_dashboard.sh   # React dashboard on :5173
```

## 4. Inputs you need to provide

| Input | Where it goes | Required? |
|---|---|---|
| Kaggle API token | `.env` (`KAGGLE_USERNAME`, `KAGGLE_KEY`) | Only for auto-download; you may instead drop clips into `data/raw_clips/` manually |
| Compliance policy PDF | `data/policy/compliance_policy.pdf` | Yes — this is the document the Policy Agent indexes |

## 5. Repository structure

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#5-repository-layout) for
the full annotated tree.

## 6. Documentation index

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system diagrams, agent responsibilities, data flow
- [`docs/ABM_DESIGN.md`](docs/ABM_DESIGN.md) — ABM algorithm choice and justification
- [`docs/GREEN_AI.md`](docs/GREEN_AI.md) — compute/memory/energy analysis per component
- [`docs/SWARM_INTELLIGENCE.md`](docs/SWARM_INTELLIGENCE.md) — ACO/PSO research extensions (adaptive risk scoring, threshold tuning, detector consensus, resource-aware scheduling)
- [`docs/EVALUATION.md`](docs/EVALUATION.md) — evaluation metrics and methodology (detection, policy grounding fidelity, severity agreement, resource footprint)
- Each `src/<agent>/README.md` (added per phase) — module-level design notes

## 7. License & confidentiality note

This repository is a technical implementation built from a publicly
described systems brief; it contains no proprietary text from any
third-party assessment document.
