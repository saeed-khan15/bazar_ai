# utils/embeddings.py
import numpy as np
import streamlit as st


@st.cache_resource(show_spinner="Loading AI model (first time only)...")
def get_embedding_model():
    """
    Load fastembed model once per container lifetime.
    @st.cache_resource means all user sessions share the same loaded model —
    no re-download on every file upload.
    """
    try:
        from fastembed import TextEmbedding
        return TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    except Exception:
        return None


def embed_texts(texts):
    model = get_embedding_model()
    if model is None or not texts:
        return None  # None not zeros — callers must check explicitly
    try:
        embeddings = list(model.embed(texts))
        return np.array(embeddings, dtype="float32")
    except Exception:
        return None


def build_faiss_index(chunks):
    """
    Build FAISS index from text chunks.
    Returns (index, chunks) where index is None if model unavailable.
    Caller should handle None index — semantic_search already does this gracefully.
    """
    import faiss
    if not chunks:
        return None, []

    embeddings = embed_texts(chunks)

    # FIXED: previously returned zeros on model failure, which built a real but
    # poisoned FAISS index — every query matched every chunk equally.
    # Now we return None so semantic_search falls back to first-k chunks instead.
    if embeddings is None or embeddings.shape[0] == 0:
        return None, chunks

    dim = embeddings.shape[1]
    faiss.normalize_L2(embeddings)
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    return index, chunks


def semantic_search(query, index, chunks, k=5):
    """
    Retrieve top-k relevant chunks for a query.
    Falls back to first-k chunks if index is None (model unavailable).
    """
    if index is None or not chunks:
        return chunks[:k] if chunks else []
    try:
        import faiss
        q_emb = embed_texts([query])
        if q_emb is None:
            return chunks[:k]
        faiss.normalize_L2(q_emb)
        distances, indices = index.search(q_emb, min(k, len(chunks)))
        results = [chunks[idx] for idx in indices[0] if 0 <= idx < len(chunks)]
        return results if results else chunks[:k]
    except Exception:
        return chunks[:k]
