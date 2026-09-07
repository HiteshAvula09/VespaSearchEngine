from vespasearch.chunking import clean_text, chunk_text


def test_clean_text():
    assert clean_text("a   b\r\n\r\n\r\nc") == "a b\n\nc"


def test_chunk():
    chunks = chunk_text("Paragraph one.\n\nParagraph two.", size=25, overlap=5)
    assert chunks
