import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from src.documents.processor import extract_pages, smart_chunks, sha256_bytes
from src.utils.config import (
    DOC_DIR, INDEX_DIR, EMBEDDING_MODEL
)

INDEX_FILE = INDEX_DIR / "vectors.faiss"
META_FILE = INDEX_DIR / "metadata.json"
MANIFEST_FILE = INDEX_DIR / "manifest.json"

_model = None

def model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model

def manifest():
    result = {}
    for path in sorted(DOC_DIR.glob("*.pdf")):
        result[path.name] = {
            "size": path.stat().st_size,
            "mtime": path.stat().st_mtime_ns
        }
    return result

def build(force=False):
    current = manifest()
    old = {}
    if MANIFEST_FILE.exists():
        try:
            old = json.loads(MANIFEST_FILE.read_text())
        except Exception:
            old = {}

    if not force and current == old and INDEX_FILE.exists() and META_FILE.exists():
        metadata = json.loads(META_FILE.read_text(encoding="utf-8"))
        return len(current), len(metadata)

    all_chunks = []
    for filename in current:
        path = DOC_DIR / filename
        all_chunks.extend(
            smart_chunks(extract_pages(path), filename)
        )

    if not all_chunks:
        for f in (INDEX_FILE, META_FILE, MANIFEST_FILE):
            if f.exists():
                f.unlink()
        return 0, 0

    vectors = model().encode(
        [c["text"] for c in all_chunks],
        normalize_embeddings=True,
        batch_size=32,
        show_progress_bar=False
    ).astype("float32")

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    faiss.write_index(index, str(INDEX_FILE))
    META_FILE.write_text(
        json.dumps(all_chunks, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    MANIFEST_FILE.write_text(
        json.dumps(current, indent=2),
        encoding="utf-8"
    )
    return len(current), len(all_chunks)

def load():
    if not INDEX_FILE.exists() or not META_FILE.exists():
        return None, []
    return (
        faiss.read_index(str(INDEX_FILE)),
        json.loads(META_FILE.read_text(encoding="utf-8"))
    )
