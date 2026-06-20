"""
src/policy_agent/build_index.py

Runs the full offline indexing pipeline:
    PDF -> sections -> chunks -> embeddings -> FAISS index (+ metadata json)

Run directly:
    python3 -m src.policy_agent.build_index

Writes two files into vector_store/:
    policy.index        (FAISS IndexFlatIP, binary)
    policy_meta.json     (chunk_id -> text/section_ref/callout/page mapping)
"""
import json

import faiss

from src.common.config import load_config, resolve_path
from src.common.logging_utils import get_logger
from src.policy_agent.pdf_parser import extract_pages, split_into_sections
from src.policy_agent.chunker import chunk_sections
from src.policy_agent.embedder import embed_texts

logger = get_logger(__name__)


def build_index(config: dict | None = None) -> None:
    cfg = config or load_config()
    pa_cfg = cfg["policy_agent"]

    pdf_path = resolve_path(cfg["paths"]["policy_pdf"])
    vector_dir = resolve_path(cfg["paths"]["vector_store_dir"] + "/_placeholder").parent
    index_path = vector_dir / "policy.index"
    meta_path = vector_dir / "policy_meta.json"

    logger.info(f"Building policy vector store from {pdf_path}")
    pages = extract_pages(pdf_path)
    sections = split_into_sections(pages)
    chunks = chunk_sections(
        sections,
        chunk_size_tokens=pa_cfg["chunk_size_tokens"],
        chunk_overlap_tokens=pa_cfg["chunk_overlap_tokens"],
    )

    if not chunks:
        raise RuntimeError(
            "No text extracted from the policy PDF — it may be a scanned "
            "image PDF requiring OCR, which is out of scope for this "
            "offline-RAG implementation. See docs/GREEN_AI.md."
        )

    texts = [c.text for c in chunks]
    embeddings = embed_texts(texts, model_name=pa_cfg["embedding_model"])
    dim = embeddings.shape[1]

    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    faiss.write_index(index, str(index_path))

    metadata = [
        {
            "chunk_id": c.chunk_id,
            "text": c.text,
            "section_ref": c.section_ref,
            "callout": c.callout,
            "page_number": c.page_number,
            "vector_row": i,
        }
        for i, c in enumerate(chunks)
    ]
    with open(meta_path, "w") as f:
        json.dump(
            {"embedding_model": pa_cfg["embedding_model"], "chunks": metadata},
            f,
            indent=2,
        )

    logger.info(
        f"Wrote FAISS index ({index.ntotal} vectors, dim={dim}) to {index_path}"
    )
    logger.info(f"Wrote chunk metadata to {meta_path}")


if __name__ == "__main__":
    build_index()
