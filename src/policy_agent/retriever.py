"""
src/policy_agent/retriever.py

Loads the pre-built FAISS index + metadata and exposes a single retrieve()
function: embed the query locally, search the index, return the top-k
policy chunks with their section_ref/callout, so every downstream
detection or severity decision can cite the exact policy text it came from.

This is the entire "retrieval-based rule reasoning" stage — no generative
model is used to answer the query; the system returns the actual retrieved
policy passages and lets the calling agent (Vision/Risk) apply deterministic
logic on top of them. This is a deliberate design choice: it keeps the
"how do you verify the LLM's output is faithful to the source" risk (raised
in the assignment's own hints) from existing in the first place, since
nothing is generated — only retrieved.
"""
import json
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np

from src.common.config import load_config, resolve_path
from src.common.logging_utils import get_logger
from src.policy_agent.embedder import embed_texts

logger = get_logger(__name__)


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    section_ref: str
    callout: str | None
    page_number: int
    score: float


class PolicyRetriever:
    def __init__(self, config: dict | None = None):
        self.cfg = config or load_config()
        pa_cfg = self.cfg["policy_agent"]
        self.embedding_model = pa_cfg["embedding_model"]
        self.top_k_default = pa_cfg["top_k_retrieval"]

        vector_dir = resolve_path(self.cfg["paths"]["vector_store_dir"] + "/_p").parent
        self.index_path = vector_dir / "policy.index"
        self.meta_path = vector_dir / "policy_meta.json"

        self.index = None
        self.chunks: list[dict] = []
        self._load()

    def _load(self):
        if not self.index_path.exists() or not self.meta_path.exists():
            raise FileNotFoundError(
                "Policy vector store not found. Run "
                "`python3 -m src.policy_agent.build_index` first "
                "(setup.sh does this automatically when the policy PDF is present)."
            )
        self.index = faiss.read_index(str(self.index_path))
        with open(self.meta_path) as f:
            data = json.load(f)
        self.chunks = data["chunks"]
        logger.info(f"Loaded policy index with {len(self.chunks)} chunks")

    def retrieve(self, query: str, k: int | None = None) -> list[RetrievedChunk]:
        k = k or self.top_k_default
        query_vec = embed_texts([query], model_name=self.embedding_model)
        scores, indices = self.index.search(query_vec, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            meta = self.chunks[idx]
            results.append(
                RetrievedChunk(
                    chunk_id=meta["chunk_id"],
                    text=meta["text"],
                    section_ref=meta["section_ref"],
                    callout=meta["callout"],
                    page_number=meta["page_number"],
                    score=float(score),
                )
            )
        return results

    def retrieve_for_behavior_class(
        self, behavior_label: str, aspect: str = "definition", k: int | None = None
    ) -> list[RetrievedChunk]:
        """Convenience wrapper used by the Vision/Risk agents. `aspect`
        steers the query toward a particular kind of policy language, e.g.
        "definition", "observable indicator", "severity OR WARNING OR
        CRITICAL SAFETY NOTICE"."""
        query = f"{behavior_label} {aspect}"
        return self.retrieve(query, k=k)


_singleton: PolicyRetriever | None = None


def get_retriever(config: dict | None = None) -> PolicyRetriever:
    global _singleton
    if _singleton is None:
        _singleton = PolicyRetriever(config)
    return _singleton
