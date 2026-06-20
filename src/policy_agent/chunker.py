"""
src/policy_agent/chunker.py

Splits ParsedSection text into overlapping chunks sized for the embedding
model's effective context, while keeping each chunk's section_ref and
callout metadata intact. Overlap prevents a rule definition from being
silently split across a chunk boundary and missed at retrieval time.

A simple whitespace-token approximation is used instead of a real tokenizer
to avoid pulling in a second heavy dependency just for chunk sizing
(Green AI: one less model load).
"""
from dataclasses import dataclass, field
import uuid

from src.policy_agent.pdf_parser import ParsedSection
from src.common.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class PolicyChunk:
    chunk_id: str
    text: str
    section_ref: str
    callout: str | None
    page_number: int


def _approx_tokens(text: str) -> list[str]:
    return text.split()


def chunk_sections(
    sections: list[ParsedSection],
    chunk_size_tokens: int = 220,
    chunk_overlap_tokens: int = 40,
) -> list[PolicyChunk]:
    chunks: list[PolicyChunk] = []

    for section in sections:
        tokens = _approx_tokens(section.text)
        if not tokens:
            continue

        if len(tokens) <= chunk_size_tokens:
            chunks.append(
                PolicyChunk(
                    chunk_id=str(uuid.uuid4()),
                    text=section.text,
                    section_ref=section.section_ref,
                    callout=section.callout,
                    page_number=section.page_number,
                )
            )
            continue

        start = 0
        while start < len(tokens):
            end = min(start + chunk_size_tokens, len(tokens))
            chunk_text = " ".join(tokens[start:end])
            chunks.append(
                PolicyChunk(
                    chunk_id=str(uuid.uuid4()),
                    text=chunk_text,
                    section_ref=section.section_ref,
                    callout=section.callout,
                    page_number=section.page_number,
                )
            )
            if end == len(tokens):
                break
            start = end - chunk_overlap_tokens

    logger.info(f"Produced {len(chunks)} chunk(s) from {len(sections)} section(s)")
    return chunks
