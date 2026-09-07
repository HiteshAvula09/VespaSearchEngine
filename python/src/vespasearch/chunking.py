import re


def clean_text(text: str) -> str:
    text = text or ""
    text = text.replace("\x00", " ")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, size: int = 1400, overlap: int = 180) -> list[str]:
    text = clean_text(text)
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""

    for paragraph in paragraphs:
        candidate = (current + "\n\n" + paragraph).strip() if current else paragraph

        if len(candidate) <= size:
            current = candidate
            continue

        if current:
            chunks.append(current)

        if len(paragraph) > size:
            step = max(1, size - overlap)
            start = 0
            while start < len(paragraph):
                piece = paragraph[start:start + size].strip()
                if piece:
                    chunks.append(piece)
                start += step
            current = ""
        else:
            carry = chunks[-1][-overlap:] if chunks and overlap > 0 else ""
            current = (carry + "\n\n" + paragraph).strip()

    if current:
        chunks.append(current)

    output = []
    seen = set()
    for item in chunks:
        if item and item not in seen:
            output.append(item)
            seen.add(item)
    return output
