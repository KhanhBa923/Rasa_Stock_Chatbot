import os
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
import docx

# -------- CONFIG --------
EMBED_MODEL_NAME = "./paraphrase-multilingual-mpnet-base-v2"
CHUNK_SIZE = 500              # số ký tự mỗi chunk
CHUNK_OVERLAP = 100           # chồng lấn để giữ ngữ cảnh
EMBED_DIR = Path(__file__).resolve().parent.parent / "embeddings"
EMBED_FILE = EMBED_DIR / "doc_index.npz"
META_FILE = EMBED_DIR / "doc_meta.json"


# -------- LOADERS --------
def load_txt(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_pdf(path: Path) -> str:
    text_parts = []
    with open(path, "rb") as f:
        reader = PdfReader(f)
        for i, page in enumerate(reader.pages):
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            if t.strip():
                # thêm dấu trang (page marker) để truy xuất nguồn
                text_parts.append(f"[PAGE {i+1}] {t}")
    return "\n".join(text_parts)


def load_docx(path: Path) -> str:
    d = docx.Document(str(path))
    parts = []
    for para in d.paragraphs:
        txt = para.text.strip()
        if txt:
            parts.append(txt)
    return "\n".join(parts)


def load_document(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return load_pdf(path)
    if ext == ".docx":
        return load_docx(path)
    if ext in (".txt", ".md"):
        return load_txt(path)
    raise ValueError(f"Không hỗ trợ định dạng: {ext}")


# -------- CHUNKING --------
def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Cắt text thành đoạn nhỏ để embedding tốt hơn.
    """
    if not text:
        return []
    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap  # trượt có overlap
        if start < 0:
            start = 0
        if start >= length:
            break
    return chunks


# -------- BUILD INDEX --------
def build_embedding_index(docs_dir: Path, embed_model_name: str = EMBED_MODEL_NAME):
    EMBED_DIR.mkdir(parents=True, exist_ok=True)

    model = SentenceTransformer(embed_model_name)

    all_chunks: List[str] = []
    meta: List[Dict] = []

    for file_path in docs_dir.glob("**/*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in (".pdf", ".docx", ".txt", ".md"):
            continue

        full_text = load_document(file_path)
        chunks = chunk_text(full_text)
        for idx, ch in enumerate(chunks):
            all_chunks.append(ch)
            meta.append({
                "source": str(file_path),
                "chunk_id": idx,
            })

    if not all_chunks:
        raise RuntimeError("Không có dữ liệu để tạo embedding.")

    print(f"Embedding {len(all_chunks)} đoạn văn...")
    embeddings = model.encode(all_chunks, batch_size=32, show_progress_bar=True, convert_to_numpy=True, normalize_embeddings=True)

    # lưu
    np.savez_compressed(EMBED_FILE, embeddings=embeddings)
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump({"chunks": meta, "texts": all_chunks}, f, ensure_ascii=False, indent=2)

    print(f"✅ Đã lưu embeddings: {EMBED_FILE}")
    print(f"✅ Đã lưu metadata:   {META_FILE}")


# -------- RUNTIME LOADER (dùng trong action) --------
_cached_embeddings = None
_cached_texts = None
_cached_meta = None
_cached_model = None


def load_vector_store() -> Tuple[np.ndarray, List[str], List[Dict], SentenceTransformer]:
    global _cached_embeddings, _cached_texts, _cached_meta, _cached_model

    if _cached_embeddings is not None and _cached_texts is not None and _cached_meta is not None and _cached_model is not None:
        return _cached_embeddings, _cached_texts, _cached_meta, _cached_model
    if not EMBED_FILE.exists() or not META_FILE.exists():
        raise FileNotFoundError(
            f"Chưa có index. Hãy chạy build_embedding_index(docs_dir) trước. "
            f"File thiếu: {EMBED_FILE} hoặc {META_FILE}"
        )

    data = np.load(EMBED_FILE)["embeddings"]
    with open(META_FILE, "r", encoding="utf-8") as f:
        meta_blob = json.load(f)

    texts = meta_blob["texts"]
    meta = meta_blob["chunks"]

    model = SentenceTransformer(EMBED_MODEL_NAME)

    _cached_embeddings = data
    _cached_texts = texts
    _cached_meta = meta
    _cached_model = model
    return data, texts, meta, model


# -------- SEARCH --------
def semantic_search(query: str, top_k: int = 5, score_threshold: float = 0.35) -> List[Tuple[float, str, Dict]]:
    """
    Trả về danh sách (score, text, metadata).
    Score = cosine similarity.
    """
    emb_matrix, texts, meta, model = load_vector_store()
    q_emb = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
    scores = np.dot(emb_matrix, q_emb[0])  # vì đã normalize -> cos sim
    top_idx = np.argsort(scores)[::-1][:top_k]
    results = []
    for i in top_idx:
        sc = float(scores[i])
        if sc < score_threshold:
            continue
        results.append((sc, texts[i], meta[i]))
    return results

if __name__ == "__main__":
    docs_dir = Path("docs")
    build_embedding_index(docs_dir)