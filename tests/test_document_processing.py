import pytest

from utils.document_processing import (
    DocumentError,
    chunk_sections,
    clean_filename,
    extract_sections,
)


def test_extract_text_file():
    sections = extract_sections("notes.txt", "héllo\nworld".encode("utf-8"))
    assert sections == [(None, "héllo\nworld")]


def test_unsupported_extension():
    with pytest.raises(DocumentError):
        extract_sections("virus.exe", b"x")


def test_binary_text_file_is_rejected():
    with pytest.raises(DocumentError):
        extract_sections("data.txt", b"ab\x00cd")


def test_chunks_cover_text_and_overlap():
    text = " ".join(f"word{i}" for i in range(600))
    chunks = chunk_sections([(None, text)], chunk_chars=300, overlap=50)

    assert len(chunks) > 3
    assert all(len(chunk.text) <= 300 for chunk in chunks)
    assert chunks[0].text.startswith("word0")
    assert chunks[-1].text.endswith("word599")
    assert set(chunks[0].text.split()) & set(chunks[1].text.split())


def test_page_numbers_follow_the_start_of_each_chunk():
    chunks = chunk_sections(
        [(1, "alpha " * 200), (2, "beta " * 200)],
        chunk_chars=300,
        overlap=50,
    )

    assert chunks[0].page == 1
    assert chunks[-1].page == 2


def test_empty_sections_give_no_chunks():
    assert chunk_sections([(1, "  \n "), (2, "")]) == []


def test_invalid_chunk_settings():
    with pytest.raises(ValueError):
        chunk_sections([(None, "text")], chunk_chars=50)
    with pytest.raises(ValueError):
        chunk_sections([(None, "text")], chunk_chars=200, overlap=150)


def test_clean_filename():
    assert clean_filename("../../etc/pass wd.pdf") == "pass wd.pdf"
    assert clean_filename("C:\\docs\\a<b>.txt") == "a_b_.txt"
    assert clean_filename("   ") == "document"
    assert len(clean_filename("x" * 300 + ".pdf")) <= 80