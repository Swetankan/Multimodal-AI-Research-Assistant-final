from __future__ import annotations

from pdf_utils import chunk_pdf_pages, chunk_text, normalize_pdf_text, remove_duplicate_text_spans


def test_chunk_text_preserves_overlap_and_bounds() -> None:
    text = (
        "Paragraph one contains introductory material and context.\n\n"
        "Paragraph two contains methodology details and important benchmark discussion.\n\n"
        "Paragraph three closes the loop with results and conclusions."
    )

    chunks = chunk_text(text, chunk_size=80, overlap=12)

    assert len(chunks) >= 2
    assert all(chunk.strip() for chunk in chunks)
    assert "methodology" in " ".join(chunks).lower()


def test_chunk_text_rejects_empty_output_by_returning_empty_list() -> None:
    assert chunk_text("   ") == []


def test_chunk_pdf_pages_preserves_page_numbers() -> None:
    chunks = chunk_pdf_pages(
        [
            (1, "Page one has the abstract and introduction."),
            (2, "Page two has the method and results."),
        ],
        chunk_size=80,
        overlap=10,
    )

    assert [chunk.page for chunk in chunks] == [1, 2]
    assert "abstract" in chunks[0].text
    assert "method" in chunks[1].text


def test_normalize_pdf_text_repairs_common_extraction_artifacts() -> None:
    text = "The \ufb01nal model uses a hyphen-\nated token and \ufb02ow."

    normalized = normalize_pdf_text(text)

    assert "final" in normalized
    assert "hyphenated" in normalized
    assert "flow" in normalized


def test_remove_duplicate_text_spans_drops_repeated_lines() -> None:
    cleaned, duplicate_count = remove_duplicate_text_spans(
        "Header\nImportant result\nHeader\nImportant result\nConclusion"
    )

    assert duplicate_count == 2
    assert cleaned.splitlines() == ["Header", "Important result", "Conclusion"]
