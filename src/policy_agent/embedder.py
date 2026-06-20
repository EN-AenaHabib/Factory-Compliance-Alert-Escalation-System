"""
src/policy_agent/embedder.py

Thin wrapper around a local sentence-transformers model. No network calls
at inference time (the model weights are downloaded once on first use and
cached by the library under ~/.cache/torch/sentence_transformers — this is
the only "download" the Policy Agent ever does, and it is a one-time, local
artifact, not a per-query API call).
"""
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from src.common.logging_utils import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _get_model(model_name: str) -> SentenceTransformer:
    logger.info(f"Loading local embedding model: {model_name}")
    return SentenceTransformer(model_name)


def embed_texts(texts: list[str], model_name: str) -> np.ndarray:
    """Returns an (N, D) float32 array of L2-normalized embeddings, ready
    for inner-product (cosine) search in FAISS."""
    if not texts:
        return np.zeros((0, 384), dtype="float32")
    model = _get_model(model_name)
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=32,
    )
    return embeddings.astype("float32")
