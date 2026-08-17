import hashlib
import re
from pathlib import Path

from pypdf import PdfReader
from src.utils.config import CHUNK_SIZE, CHUNK_OVERLAP

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

def extract_pages(path):
    reader = PdfReader(str(path))
    pages = []
    for page_number, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if text:
            pages.append({
                "page": page_number,
                "text": text
            })
    return pages

def smart_chunks(pages, filename):
    chunks = []
    for page in pages:
        paragraphs = [
            re.sub(r"\s+", " ", p).strip()
            for p in re.split(r"\n\s*\n", page["text"])
            if p.strip()
        ]
        buffer = ""

        for paragraph in paragraphs:
            if len(paragraph) > CHUNK_SIZE:
                if buffer:
                    chunks.append({
                        "text": buffer,
                        "source": filename,
                        "page": page["page"]
                    })
                    buffer = ""

                start = 0
                while start < len(paragraph):
                    end = min(start + CHUNK_SIZE, len(paragraph))
                    piece = paragraph[start:end].strip()
                    if piece:
                        chunks.append({
                            "text": piece,
                            "source": filename,
                            "page": page["page"]
                        })
                    if end >= len(paragraph):
                        break
                    start = max(end - CHUNK_OVERLAP, start + 1)
            else:
                candidate = f"{buffer} {paragraph}".strip()
                if len(candidate) <= CHUNK_SIZE:
                    buffer = candidate
                else:
                    if buffer:
                        chunks.append({
                            "text": buffer,
                            "source": filename,
                            "page": page["page"]
                        })
                    overlap = buffer[-CHUNK_OVERLAP:] if buffer else ""
                    buffer = f"{overlap} {paragraph}".strip()

        if buffer:
            chunks.append({
                "text": buffer,
                "source": filename,
                "page": page["page"]
            })

    for i, chunk in enumerate(chunks):
        chunk["chunk_id"] = i
    return chunks
