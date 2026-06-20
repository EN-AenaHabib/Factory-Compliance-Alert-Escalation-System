"""
src/policy_agent/pdf_parser.py

Extracts text from the compliance policy PDF, page by page, and does light
structural parsing to recover section headers (e.g., "Section 3.3.2",
"WARNING", "CRITICAL SAFETY NOTICE") so each downstream chunk can carry a
policy_rule_ref back to its source — required by Module 4's
policy_rule_ref field and by the "traceable to the relevant policy section"
requirement in the assignment brief.

No OCR, no layout-ML model: pypdf's text extraction is sufficient for a
born-digital policy PDF and keeps this stage CPU-light (Green AI).
"""
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from src.common.logging_utils import get_logger

logger = get_logger(__name__)

# Matches things like "Section 3.3.2", "3.3.2", "Section 4:" at line start
SECTION_HEADER_RE = re.compile(
    r"^(Section\s+\d+(\.\d+)*\.?|^\d+(\.\d+)+\.?)\s*[:\-]?\s*(.*)$",
    re.IGNORECASE,
)
CALLOUT_RE = re.compile(r"\b(WARNING|CRITICAL SAFETY NOTICE)\b", re.IGNORECASE)


@dataclass
class PageText:
    page_number: int
    text: str


@dataclass
class ParsedSection:
    section_ref: str          # e.g. "Section 3.3.2" or "Page 4" if no header found
    callout: str | None       # "WARNING" / "CRITICAL SAFETY NOTICE" / None
    text: str
    page_number: int


def extract_pages(pdf_path: Path) -> list[PageText]:
    if not pdf_path.exists():
        raise FileNotFoundError(
            f"Policy PDF not found at {pdf_path}. Place the compliance "
            f"policy document there before building the index."
        )
    reader = PdfReader(str(pdf_path))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append(PageText(page_number=i + 1, text=text))
    logger.info(f"Extracted text from {len(pages)} page(s) of {pdf_path.name}")
    return pages


def split_into_sections(pages: list[PageText]) -> list[ParsedSection]:
    """
    Walk extracted text line-by-line and group it into sections keyed by
    the most recent recognized section header. Falls back to "Page N" as
    the section_ref when no explicit header is found on that page, so
    every chunk still carries SOME traceable reference, per the policy
    grounding requirement.
    """
    sections: list[ParsedSection] = []
    current_ref = None
    current_callout = None
    current_lines: list[str] = []
    current_page = 1

    def flush():
        if current_lines:
            sections.append(
                ParsedSection(
                    section_ref=current_ref or f"Page {current_page}",
                    callout=current_callout,
                    text="\n".join(current_lines).strip(),
                    page_number=current_page,
                )
            )

    for page in pages:
        for raw_line in page.text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            header_match = SECTION_HEADER_RE.match(line)
            if header_match:
                flush()
                current_ref = header_match.group(1).rstrip(".:").strip()
                if not current_ref.lower().startswith("section"):
                    current_ref = f"Section {current_ref}"
                current_lines = [line]
                current_callout = None
                current_page = page.page_number
                continue

            callout_match = CALLOUT_RE.search(line)
            if callout_match:
                current_callout = callout_match.group(1).upper()

            current_lines.append(line)
            current_page = page.page_number

    flush()
    logger.info(f"Parsed {len(sections)} section(s) from policy document")
    return sections
