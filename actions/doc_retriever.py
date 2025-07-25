import os
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from sentence_transformers import SentenceTransformer, util
import logging
import re
from difflib import SequenceMatcher

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CONFIG ====================
EMBED_MODEL_NAME = "./paraphrase-multilingual-mpnet-base-v2"
EMBED_FILE = Path("vector_store/embeddings.npz")
META_FILE = Path("vector_store/meta.json")
DOCS_DIR = Path("docs")

# ==================== CACHE ====================
_cached_embeddings = None
_cached_texts = None
_cached_meta = None
_cached_model = None


def load_model() -> SentenceTransformer:
    """Load and cache the sentence transformer model."""
    global _cached_model
    if _cached_model is None:
        logger.info(f"Loading SentenceTransformer model from: {EMBED_MODEL_NAME}")
        try:
            _cached_model = SentenceTransformer(EMBED_MODEL_NAME)
            logger.info("Model loaded successfully!")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    else:
        logger.debug("Model already cached.")
    return _cached_model


def build_embedding_index(docs_dir: Path) -> None:
    """
    Read all documents in docs_dir, split into chunks and create embeddings.
    
    Args:
        docs_dir: Directory containing documents to index
    """
    if not docs_dir.exists():
        raise FileNotFoundError(f"Documents directory not found: {docs_dir}")
    
    logger.info(f"Building embedding index from {docs_dir}...")
    model = load_model()

    texts = []
    meta = []
    
    # Supported file extensions
    supported_extensions = {".txt", ".md", ".json"}
    
    files_processed = 0
    for file_path in docs_dir.glob("**/*"):
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
            try:
                logger.info(f"Reading file: {file_path}")
                with open(file_path, "r", encoding="utf-8", errors='ignore') as f:
                    content = f.read().strip()
                
                if not content:
                    logger.warning(f"Empty file skipped: {file_path}")
                    continue

                # Split into chunks
                chunks = chunk_text(content, max_words=100)
                logger.info(f"{len(chunks)} chunks created for file {file_path.name}")

                for i, chunk in enumerate(chunks):
                    if chunk.strip():  # Only add non-empty chunks
                        texts.append(chunk.strip())
                        meta.append({
                            "file": str(file_path), 
                            "chunk_id": i,
                            "filename": file_path.name
                        })
                
                files_processed += 1
                
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                continue

    if not texts:
        raise ValueError("No valid text chunks found in the documents directory")
    
    logger.info(f"Processed {files_processed} files, created {len(texts)} chunks")
    logger.info("Creating embeddings for all chunks...")
    
    try:
        # Process in batches to handle memory efficiently
        batch_size = 100
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = model.encode(
                batch_texts, 
                show_progress_bar=True, 
                convert_to_numpy=True,
                normalize_embeddings=True  # Normalize for cosine similarity
            )
            all_embeddings.append(batch_embeddings)
        
        embeddings = np.vstack(all_embeddings)
        logger.info(f"Embedding shape: {embeddings.shape}")

        # Save data
        os.makedirs("vector_store", exist_ok=True)
        np.savez_compressed(EMBED_FILE, embeddings=embeddings)
        
        with open(META_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"texts": texts, "chunks": meta}, 
                f, 
                ensure_ascii=False, 
                indent=2
            )
        
        logger.info(f"Embedding index saved: {EMBED_FILE}, {META_FILE}")
        
    except Exception as e:
        logger.error(f"Error creating embeddings: {e}")
        raise


def extract_relevant_sentences(text: str, query: str, max_sentences: int = 3) -> str:
    """
    Trích xuất các câu có liên quan nhất đến truy vấn từ một đoạn text.
    
    Args:
        text: Đoạn text gốc
        query: Truy vấn tìm kiếm
        max_sentences: Số câu tối đa trả về
        
    Returns:
        Chuỗi chứa các câu liên quan nhất
    """
    # Tách thành các câu
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return text
    
    query_words = set(query.lower().split())
    scored_sentences = []
    
    for sentence in sentences:
        sentence_words = set(sentence.lower().split())
        
        # Tính điểm dựa trên:
        # 1. Số từ khóa chung
        common_words = query_words.intersection(sentence_words)
        word_overlap_score = len(common_words) / len(query_words) if query_words else 0
        
        # 2. Độ tương tự chuỗi
        similarity_score = SequenceMatcher(None, query.lower(), sentence.lower()).ratio()
        
        # 3. Độ dài câu (ưu tiên câu có độ dài vừa phải)
        length_score = 1.0 - abs(len(sentence.split()) - 15) / 50
        length_score = max(0, length_score)
        
        # Tổng điểm
        total_score = (word_overlap_score * 0.5 + 
                      similarity_score * 0.3 + 
                      length_score * 0.2)
        
        if total_score > 0:
            scored_sentences.append((total_score, sentence))
    
    # Sắp xếp theo điểm và lấy top câu
    scored_sentences.sort(reverse=True, key=lambda x: x[0])
    top_sentences = [sentence for _, sentence in scored_sentences[:max_sentences]]
    
    return " ".join(top_sentences) if top_sentences else text


def extract_relevant_context(text: str, query: str, context_length: int = 200) -> str:
    """
    Trích xuất đoạn văn bản ngắn xung quanh từ khóa liên quan nhất.
    
    Args:
        text: Đoạn text gốc
        query: Truy vấn tìm kiếm
        context_length: Độ dài ngữ cảnh (số ký tự)
        
    Returns:
        Đoạn văn bản ngắn chứa thông tin liên quan
    """
    query_words = query.lower().split()
    text_lower = text.lower()
    
    # Tìm vị trí tốt nhất để trích xuất
    best_position = 0
    best_score = 0
    
    # Duyệt qua text với sliding window
    window_size = context_length
    for i in range(0, len(text) - window_size + 1, 20):  # Bước nhỏ để tìm vị trí tốt
        window = text_lower[i:i + window_size]
        
        # Đếm số từ khóa trong window
        score = sum(1 for word in query_words if word in window)
        
        if score > best_score:
            best_score = score
            best_position = i
    
    # Trích xuất đoạn văn tại vị trí tốt nhất
    if best_score > 0:
        # Điều chỉnh để bắt đầu và kết thúc tại ranh giới từ
        start = best_position
        end = min(best_position + context_length, len(text))
        
        # Tìm ranh giới từ gần nhất
        while start > 0 and text[start] != ' ':
            start -= 1
        while end < len(text) - 1 and text[end] != ' ':
            end += 1
        
        extracted = text[start:end].strip()
        
        # Thêm dấu ... nếu không phải đầu/cuối văn bản
        if start > 0:
            extracted = "..." + extracted
        if end < len(text) - 1:
            extracted = extracted + "..."
            
        return extracted
    
    # Fallback: trả về phần đầu của text
    return text[:context_length] + ("..." if len(text) > context_length else "")
def chunk_text(text: str, max_words: int = 100, overlap_words: int = 20) -> List[str]:
    """
    Split text into chunks with specified max words and optional overlap.
    
    Args:
        text: Input text to chunk
        max_words: Maximum words per chunk
        overlap_words: Number of overlapping words between chunks
        
    Returns:
        List of text chunks
    """
    if not text.strip():
        return []
    
    words = text.split()
    if len(words) <= max_words:
        return [text]
    
    chunks = []
    step = max_words - overlap_words
    
    for i in range(0, len(words), step):
        chunk_words = words[i:i + max_words]
        chunk = " ".join(chunk_words)
        chunks.append(chunk)
        
        # Stop if we've covered all words
        if i + max_words >= len(words):
            break
    
    return chunks


def load_vector_store() -> Tuple[np.ndarray, List[str], List[Dict], SentenceTransformer]:
    """Load vector store from cache or files."""
    global _cached_embeddings, _cached_texts, _cached_meta, _cached_model

    if _cached_embeddings is not None:
        logger.debug("Vector store already loaded from cache.")
        return _cached_embeddings, _cached_texts, _cached_meta, _cached_model # type: ignore

    if not EMBED_FILE.exists() or not META_FILE.exists():
        raise FileNotFoundError(
            "Embedding index not found. Please run build_embedding_index(docs_dir) first."
        )

    try:
        logger.info("Loading embeddings from file...")
        data = np.load(EMBED_FILE)["embeddings"]

        with open(META_FILE, "r", encoding="utf-8") as f:
            meta_blob = json.load(f)

        texts = meta_blob["texts"]
        meta = meta_blob["chunks"]
        model = load_model()

        # Cache the loaded data
        _cached_embeddings = data
        _cached_texts = texts
        _cached_meta = meta
        _cached_model = model
        
        logger.info(f"Loaded {len(texts)} chunks with shape {data.shape}")
        return data, texts, meta, model
        
    except Exception as e:
        logger.error(f"Error loading vector store: {e}")
        raise


def retrieve_answer(
    query: str, 
    top_k: int = 5, 
    score_threshold: float = 0.35,
    extract_mode: str = "sentences"  # "sentences", "context", "full"
) -> List[Tuple[float, str, Dict]]:
    """
    Search for answers from embedding index using cosine similarity.
    
    Args:
        query: Search query
        top_k: Number of top results to return
        score_threshold: Minimum similarity score threshold
        extract_mode: How to extract relevant information:
                     - "sentences": Extract most relevant sentences
                     - "context": Extract relevant context around keywords
                     - "full": Return full chunk (original behavior)
        
    Returns:
        List of tuples: [(score, extracted_text, metadata), ...]
    """
    if not query.strip():
        return []
    
    try:
        embeddings, texts, meta, model = load_vector_store()

        # Create query embedding (normalized)
        query_emb = model.encode(
            [query], 
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        # Calculate cosine similarity (since embeddings are normalized, dot product = cosine similarity)
        scores = np.dot(embeddings, query_emb.T).squeeze()

        # Get top results
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        
        for idx in top_indices:
            score = float(scores[idx])
            if score >= score_threshold:
                original_text = texts[idx]
                
                # Trích xuất thông tin liên quan theo mode
                if extract_mode == "sentences":
                    extracted_text = extract_relevant_sentences(original_text, query)
                elif extract_mode == "context":
                    extracted_text = extract_relevant_context(original_text, query)
                else:  # "full"
                    extracted_text = original_text
                
                # Thêm thông tin gốc vào metadata để tham khảo
                enhanced_meta = meta[idx].copy()
                enhanced_meta["original_text"] = original_text
                enhanced_meta["extraction_mode"] = extract_mode
                
                results.append((score, extracted_text, enhanced_meta))
        
        logger.info(f"Found {len(results)} results above threshold {score_threshold}")
        return results
        
    except Exception as e:
        logger.error(f"Error retrieving answers: {e}")
        return []


def smart_retrieve(
    query: str, 
    top_k: int = 5, 
    score_threshold: float = 0.35
) -> List[Tuple[float, str, Dict]]:
    """
    Tìm kiếm thông minh, tự động chọn phương pháp trích xuất tốt nhất.
    
    Args:
        query: Truy vấn tìm kiếm
        top_k: Số kết quả trả về
        score_threshold: Ngưỡng điểm tối thiểu
        
    Returns:
        List of tuples với thông tin được trích xuất thông minh
    """
    # Lấy kết quả với cả 3 phương pháp
    sentence_results = retrieve_answer(query, top_k, score_threshold, "sentences")
    context_results = retrieve_answer(query, top_k, score_threshold, "context")
    
    combined_results = []
    
    for i in range(min(len(sentence_results), len(context_results))):
        score = sentence_results[i][0]
        sentence_text = sentence_results[i][1]
        context_text = context_results[i][1]
        metadata = sentence_results[i][2]
        
        # Chọn phương pháp tốt hơn dựa trên độ dài và chất lượng
        if len(sentence_text.strip()) > 20 and len(sentence_text.split('.')) >= 1:
            # Ưu tiên sentences nếu có câu hoàn chỉnh
            final_text = sentence_text
            extraction_method = "sentences"
        elif len(context_text.strip()) > 10:
            # Fallback sang context
            final_text = context_text
            extraction_method = "context"
        else:
            # Cuối cùng dùng original text
            final_text = metadata.get("original_text", sentence_text)
            extraction_method = "full"
        
        metadata["extraction_method"] = extraction_method
        combined_results.append((score, final_text, metadata))
    
    return combined_results


def search_with_context(
    query: str, 
    top_k: int = 5, 
    score_threshold: float = 0.35,
    context_window: int = 1
) -> List[Tuple[float, str, Dict]]:
    """
    Enhanced search that includes context from adjacent chunks.
    
    Args:
        query: Search query
        top_k: Number of top results to return
        score_threshold: Minimum similarity score threshold
        context_window: Number of adjacent chunks to include as context
        
    Returns:
        List of tuples with context: [(score, text_with_context, metadata), ...]
    """
    results = retrieve_answer(query, top_k, score_threshold)
    
    if not results or context_window == 0:
        return results
    
    try:
        _, texts, meta, _ = load_vector_store()
        enhanced_results = []
        
        for score, text, metadata in results:
            # Find the original chunk index
            original_idx = None
            for i, m in enumerate(meta):
                if (m.get('file') == metadata.get('file') and 
                    m.get('chunk_id') == metadata.get('chunk_id')):
                    original_idx = i
                    break
            
            if original_idx is not None:
                # Get context chunks from the same file
                same_file_chunks = []
                for i, m in enumerate(meta):
                    if m.get('file') == metadata.get('file'):
                        same_file_chunks.append((i, m.get('chunk_id', 0)))
                
                # Sort by chunk_id
                same_file_chunks.sort(key=lambda x: x[1])
                
                # Find position in same-file chunks
                pos = None
                for j, (idx, _) in enumerate(same_file_chunks):
                    if idx == original_idx:
                        pos = j
                        break
                
                if pos is not None:
                    # Get context chunks
                    start = max(0, pos - context_window)
                    end = min(len(same_file_chunks), pos + context_window + 1)
                    
                    context_texts = []
                    for j in range(start, end):
                        chunk_idx = same_file_chunks[j][0]
                        context_texts.append(texts[chunk_idx])
                    
                    enhanced_text = " ... ".join(context_texts)
                    enhanced_results.append((score, enhanced_text, metadata))
                else:
                    enhanced_results.append((score, text, metadata))
            else:
                enhanced_results.append((score, text, metadata))
        
        return enhanced_results
        
    except Exception as e:
        logger.error(f"Error adding context: {e}")
        return results


def clear_cache() -> None:
    """Clear all cached data."""
    global _cached_embeddings, _cached_texts, _cached_meta, _cached_model
    _cached_embeddings = None
    _cached_texts = None
    _cached_meta = None
    _cached_model = None
    logger.info("Cache cleared.")


if __name__ == "__main__":
    logger.info("Testing doc_retriever_fixed.py...")

    try:
        if not EMBED_FILE.exists() or not META_FILE.exists():
            logger.info("No embedding index found. Building index...")
            build_embedding_index(DOCS_DIR)
        else:
            logger.info("Embedding index already exists. Skipping build.")

        # Test queries với các phương pháp khác nhau
        test_queries = [
            "What is Rasa",
            "Closing session",
            "Hanoi stock exchange"
        ]
        
        for query in test_queries:
            logger.info(f"Testing query: {query}")
            
            # Test smart retrieve (khuyến nghị)
            logger.info("=== SMART RETRIEVE (Recommended) ===")
            smart_answers = smart_retrieve(query, top_k=3)
            
            if smart_answers:
                for i, (score, text, metadata) in enumerate(smart_answers, 1):
                    logger.info(f"{i}. Score: {score:.3f}")
                    logger.info(f"   File: {metadata.get('filename', 'Unknown')}")
                    logger.info(f"   Method: {metadata.get('extraction_method', 'Unknown')}")
                    logger.info(f"   Extracted: {text}")
                    logger.info("-" * 50)
            else:
                logger.info("No results found.")
            
            # So sánh với phương pháp cũ
            logger.info("=== FULL CHUNK (Original) ===")
            full_answers = retrieve_answer(query, top_k=1, extract_mode="full")
            if full_answers:
                score, text, metadata = full_answers[0]
                logger.info(f"Full chunk: {text[:150]}...")
            
            logger.info("=" * 100)
            
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise