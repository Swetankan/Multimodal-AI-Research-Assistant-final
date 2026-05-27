from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass
class PdfTextChunk:
    text: str
    page: int
    source_type: str = "text"


@dataclass
class PdfExtractionResult:
    chunks: list[PdfTextChunk]
    diagnostics: dict[str, object]


LIGATURES = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
}


def normalize_pdf_text(text: str) -> str:
    normalized = text
    for ligature, replacement in LIGATURES.items():
        normalized = normalized.replace(ligature, replacement)

    normalized = re.sub(r"(\w)-\n(\w)", r"\1\2", normalized)
    normalized = re.sub(r"\r", "", normalized)
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    return normalized


def remove_duplicate_text_spans(text: str) -> tuple[str, int]:
    seen: set[str] = set()
    output: list[str] = []
    duplicate_count = 0

    for line in text.splitlines():
        compact = re.sub(r"\s+", " ", line).strip()
        if compact and compact in seen:
            duplicate_count += 1
            continue
        if compact:
            seen.add(compact)
        output.append(line)

    return "\n".join(output), duplicate_count


def extract_text_by_page(file_path: str | Path) -> list[tuple[int, str]]:
    reader = PdfReader(str(file_path))
    pages: list[tuple[int, str]] = []

    for index, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        cleaned_text, _ = remove_duplicate_text_spans(normalize_pdf_text(raw_text))
        pages.append((index, cleaned_text))

    if not any(text.strip() for _, text in pages):
        raise ValueError("The PDF did not contain extractable text.")

    return pages


def extract_text_from_pdf(file_path: str | Path) -> str:
    return "\n\n".join(text for _, text in extract_text_by_page(file_path)).strip()


def _split_long_paragraph(paragraph: str, chunk_size: int, overlap: int) -> list[str]:
    slices: list[str] = []
    start = 0
    while start < len(paragraph):
        end = min(start + chunk_size, len(paragraph))
        slices.append(paragraph[start:end].strip())
        if end >= len(paragraph):
            break
        start = max(end - overlap, 0)
    return [item for item in slices if item]


def chunk_text(text: str, chunk_size: int = 700, overlap: int = 120) -> list[str]:
    normalized = re.sub(r"\r", "", text)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
    paragraphs = [
        re.sub(r"\s+", " ", paragraph).strip()
        for paragraph in normalized.split("\n\n")
        if paragraph.strip()
    ]

    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.extend(_split_long_paragraph(paragraph, chunk_size, overlap))
            continue

        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            chunks.append(current.strip())
            current = paragraph

    if current:
        chunks.append(current.strip())

    merged: list[str] = []
    for index, chunk in enumerate(chunks):
        if index == 0:
            merged.append(chunk)
            continue
        prefix = chunks[index - 1][-overlap:].strip()
        merged.append(f"{prefix} {chunk}".strip())

    return [item for item in merged if item]


def is_figure_caption(paragraph: str) -> bool:
    return bool(re.match(r"^\s*(?:Figure|Fig\.)\s+\d+[:\.\s]", paragraph, re.IGNORECASE))


def is_table(paragraph: str) -> bool:
    if re.match(r"^\s*Table\s+\d+[:\.\s]", paragraph, re.IGNORECASE):
        return True

    lines = [line.strip() for line in paragraph.split("\n") if line.strip()]
    if len(lines) < 2:
        return False

    tabular_lines = 0
    for line in lines:
        parts = re.split(r"\t|\s{2,}", line)
        if len(parts) >= 3:
            tabular_lines += 1

    return (tabular_lines / len(lines)) >= 0.5


def chunk_pdf_pages(
    pages: list[tuple[int, str]],
    chunk_size: int = 700,
    overlap: int = 120
) -> list[PdfTextChunk]:
    chunks: list[PdfTextChunk] = []

    for page_number, text in pages:
        normalized = re.sub(r"\r", "", text)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
        paragraphs = [p.strip() for p in normalized.split("\n\n") if p.strip()]

        current_text_block = []

        for paragraph in paragraphs:
            if is_figure_caption(paragraph):
                if current_text_block:
                    text_to_chunk = "\n\n".join(current_text_block)
                    for chunk in chunk_text(text_to_chunk, chunk_size=chunk_size, overlap=overlap):
                        chunks.append(PdfTextChunk(text=chunk, page=page_number, source_type="text"))
                    current_text_block = []
                chunks.append(PdfTextChunk(text=paragraph, page=page_number, source_type="figure_caption"))

            elif is_table(paragraph):
                if current_text_block:
                    text_to_chunk = "\n\n".join(current_text_block)
                    for chunk in chunk_text(text_to_chunk, chunk_size=chunk_size, overlap=overlap):
                        chunks.append(PdfTextChunk(text=chunk, page=page_number, source_type="text"))
                    current_text_block = []
                chunks.append(PdfTextChunk(text=paragraph, page=page_number, source_type="table"))

            else:
                current_text_block.append(paragraph)

        if current_text_block:
            text_to_chunk = "\n\n".join(current_text_block)
            for chunk in chunk_text(text_to_chunk, chunk_size=chunk_size, overlap=overlap):
                chunks.append(PdfTextChunk(text=chunk, page=page_number, source_type="text"))

    return chunks


def extract_pdf_with_diagnostics(file_path: str | Path, chunk_size: int = 700) -> PdfExtractionResult:
    reader = PdfReader(str(file_path))
    pages: list[tuple[int, str]] = []
    duplicate_lines_removed = 0
    raw_characters = 0

    for index, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        raw_characters += len(raw_text)
        normalized = normalize_pdf_text(raw_text)
        deduped, duplicate_count = remove_duplicate_text_spans(normalized)
        duplicate_lines_removed += duplicate_count
        pages.append((index, deduped))

    if not any(text.strip() for _, text in pages):
        raise ValueError(
            "The PDF did not contain extractable text. It may be scanned or image-only; OCR is not enabled yet."
        )

    chunks = chunk_pdf_pages(pages, chunk_size=chunk_size)
    if not chunks:
        raise ValueError("The PDF did not contain enough extractable text to index.")

    extracted_characters = sum(len(text) for _, text in pages)
    diagnostics = {
        "total_pages": len(pages),
        "raw_characters": raw_characters,
        "extracted_characters": extracted_characters,
        "chunk_count": len(chunks),
        "table_count": len([c for c in chunks if c.source_type == "table"]),
        "figure_caption_count": len([c for c in chunks if c.source_type == "figure_caption"]),
        "empty_pages": [page_number for page_number, text in pages if not text.strip()],
        "duplicate_lines_removed": duplicate_lines_removed,
        "ligatures_normalized": True,
        "hyphenated_line_breaks_fixed": True,
        "ocr_used": False,
    }
    return PdfExtractionResult(chunks=chunks, diagnostics=diagnostics)


def extract_chunks_from_pdf(file_path: str | Path, chunk_size: int = 700) -> list[PdfTextChunk]:
    return extract_pdf_with_diagnostics(file_path, chunk_size=chunk_size).chunks
