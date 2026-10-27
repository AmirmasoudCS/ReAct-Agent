"""Extract text from uploaded files and split it into chunks."""

from __future__ import annotations

import bisect
import io
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import PurePath

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}
MAX_NAME_LENGTH = 80

_UNSAFE_NAME_CHARS = re.compile(r"[^\w .()\-]")
_WHITESPACE_RE = re.compile(r"\s")
_BREAKS = ("\n\n", "\n", ". ", "? ", "! ", " ")


class DocumentError(ValueError):
    """A problem with an uploaded file that can be shown to the user."""


@dataclass(frozen=True)
class Chunk:
    text: str
    page: int | None = None


def clean_filename(filename: str) -> str:
    """Keep only a safe display name (no paths, no odd characters)."""
    name = PurePath(str(filename).replace("\\", "/")).name
    name = _UNSAFE_NAME_CHARS.sub("_", name).strip(" .")

    if not name:
        return "document"

    if len(name) > MAX_NAME_LENGTH:
        suffix = PurePath(name).suffix[:10]
        name = name[: MAX_NAME_LENGTH - len(suffix)] + suffix

    return name


def extract_sections(
    filename: str,
    data: bytes,
) -> list[tuple[int | None, str]]:
    """Return (page, text) sections. Page is None for formats without pages."""
    extension = PurePath(filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise DocumentError(
            "Unsupported file type. Use .txt, .md, .pdf or .docx."
        )

    if extension in {".txt", ".md"}:
        return [(None, _decode_text(data))]

    if extension == ".pdf":
        return _extract_pdf(data)

    return [(None, _extract_docx(data))]


def _decode_text(data: bytes) -> str:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1252", errors="replace")

    if "\x00" in text:
        raise DocumentError("This file looks like binary data, not text.")

    return text


def _extract_pdf(data: bytes) -> list[tuple[int | None, str]]:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise DocumentError(
            "PDF support needs the 'pypdf' package (pip install pypdf)."
        ) from error

    sections: list[tuple[int | None, str]] = []

    try:
        reader = PdfReader(io.BytesIO(data))

        if reader.is_encrypted and not reader.decrypt(""):
            raise DocumentError("This PDF is password-protected.")

        for number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""

            if text.strip():
                sections.append((number, text))
    except DocumentError:
        raise
    except Exception as error:
        raise DocumentError("The PDF could not be read.") from error

    return sections


def _extract_docx(data: bytes) -> str:
    try:
        from docx import Document
    except ImportError as error:
        raise DocumentError(
            "DOCX support needs the 'python-docx' package "
            "(pip install python-docx)."
        ) from error

    try:
        document = Document(io.BytesIO(data))
        parts = [paragraph.text for paragraph in document.paragraphs]

        # Tables are appended after the paragraphs (their original
        # position in the document is not kept).
        for table in document.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                parts.append(" | ".join(cell for cell in cells if cell))
    except Exception as error:
        raise DocumentError("The DOCX file could not be read.") from error

    return "\n".join(parts)


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _find_break(text: str, start: int, end: int) -> int:
    """Prefer ending a chunk at a paragraph, line or sentence boundary."""
    window_start = start + int((end - start) * 0.6)

    for separator in _BREAKS:
        index = text.rfind(separator, window_start, end)

        if index != -1:
            return index + len(separator)

    return end


def chunk_sections(
    sections: list[tuple[int | None, str]],
    chunk_chars: int = 900,
    overlap: int = 150,
) -> list[Chunk]:
    """Split sections into overlapping chunks. A chunk's page is the page
    where it starts."""
    if chunk_chars < 100:
        raise ValueError("chunk_chars must be at least 100.")

    if not 0 <= overlap < chunk_chars // 2:
        raise ValueError("overlap must be from 0 to half of chunk_chars.")

    texts: list[str] = []
    starts: list[int] = []
    pages: list[int | None] = []
    offset = 0

    for page, raw in sections:
        text = _normalize(raw)

        if not text:
            continue

        texts.append(text)
        starts.append(offset)
        pages.append(page)
        offset += len(text) + 2  # the "\n\n" joining sections

    full = "\n\n".join(texts)
    total = len(full)
    chunks: list[Chunk] = []
    start = 0

    while start < total:
        end = min(start + chunk_chars, total)

        if end < total:
            end = _find_break(full, start, end)

        raw_piece = full[start:end]
        piece = raw_piece.strip()

        if piece:
            position = start + (len(raw_piece) - len(raw_piece.lstrip()))
            section = bisect.bisect_right(starts, position) - 1
            chunks.append(Chunk(piece, pages[section]))

        if end >= total:
            break

        # Step back by `overlap`, then move to the next word boundary so
        # a chunk never starts in the middle of a word.
        next_start = end - overlap
        boundary = _WHITESPACE_RE.search(full, next_start, end)

        if boundary:
            next_start = boundary.end()

        start = max(next_start, start + 1)

    return chunks


def embed_in_batches(
    embed: Callable[[list[str]], list[list[float]]],
    texts: list[str],
    batch_size: int = 16,
) -> list[list[float]]:
    """Embed many texts with several smaller requests."""
    vectors: list[list[float]] = []

    for index in range(0, len(texts), batch_size):
        vectors.extend(embed(texts[index:index + batch_size]))

    return vectors