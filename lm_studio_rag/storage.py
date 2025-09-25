# storage.py
from typing import Optional, List, Dict, Any
import numpy as np
import os
import json
import logging
from sentence_transformers import SentenceTransformer
from .config import VECTOR_DB_TYPE, CHROMA_PERSIST_DIR, FAISS_INDEX_PATH, METADATA_STORE_PATH, EMBEDDING_MODEL_NAME
from .utils import save_json, load_json, now_iso

logger = logging.getLogger("storage")

class RAGStorage:
    """
    Abstracted RAG storage that supports:
     - Chroma (recommended)
     - Faiss (fallback)
    Each stored document has:
     - id, text, metadata (timestamp, label, score, source)
    """

    def __init__(self, embedding_model_name: str = EMBEDDING_MODEL_NAME, dim: int = None, vector_db_type: str = VECTOR_DB_TYPE, USE_MEMORY_RUN:bool = False):
        self.dim = dim
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.vector_db_type = vector_db_type
        if vector_db_type == "chroma":
            try:
                import chromadb
                if USE_MEMORY_RUN:                    
                    self.client = chromadb.EphemeralClient()
                    self.collection = self.client.get_or_create_collection(name="rag_collection")
                    logger.info("ChromaDB initialized in-memory (ephemeral).")
                else:
                    # データベースディレクトリが存在するかどうかで、新規作成かロードかを判断しログに出力
                    if not os.path.exists(CHROMA_PERSIST_DIR):
                        logger.info("ChromaDB persistence directory not found at '%s'. A new database will be created.", CHROMA_PERSIST_DIR)
                    else:
                        logger.info("Loading ChromaDB from existing directory: '%s'", CHROMA_PERSIST_DIR)

                    # PersistentClientを使用すると、指定したパスのデータの読み込みと自動保存が行われます。
                    self.client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
                    self.collection = self.client.get_or_create_collection(name="rag_collection")
                    logger.info("ChromaDB initialized successfully.")
            except Exception as e:
                logger.warning("Chroma init failed: %s; falling back to faiss", e)
                self._init_faiss(dim or 384)
                self.vector_db_type = "faiss"
        else:
            self._init_faiss(dim or 384)

    # --- FAISS simple implementation ---
    def _init_faiss(self, dim: int):
        import faiss
        self.faiss = faiss
        self.dim = dim
        self.index = faiss.IndexFlatIP(self.dim)  # inner product (need normalized vectors)
        # metadata mapping: id -> metadata
        self.metadata = load_json(METADATA_STORE_PATH) or {}
        self.next_id = max([int(k) for k in self.metadata.keys()]) + 1 if self.metadata else 1
        logger.info("Initialized FAISS index dim=%d", self.dim)

    def _normalize(self, vecs: List[List[float]]) -> np.ndarray:
        arr = np.array(vecs, dtype=np.float32)
        # normalize for cosine similarity via inner product
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return arr / norms

    # --- Save helpers ---
    def _upsert_chroma(self, texts: List[str], metadatas: List[Dict[str, Any]], ids: Optional[List[str]] = None):
        # chroma expects ids, metadatas, documents, embeddings optional
        embs = self.embedding_model.encode(texts, show_progress_bar=False)
        self.collection.add(documents=texts, metadatas=metadatas, ids=ids, embeddings=embs)
        # PersistentClientを使用しているため、add操作は自動的に永続化されます。

    def _upsert_faiss(self, texts: List[str], metadatas: List[Dict[str, Any]]):
        embs = self.embedding_model.encode(texts, show_progress_bar=False)
        embs_norm = self._normalize(embs)
        self.index.add(embs_norm.astype('float32'))
        # store metadata with generated ids incrementally (use simple integer IDs as strings)
        for txt, meta in zip(texts, metadatas):
            id_str = str(self.next_id)
            self.metadata[id_str] = {"text": txt, "meta": meta}
            self.next_id += 1
        save_json(METADATA_STORE_PATH, self.metadata)

    def save_personality_data(self, text: str, metadata: Dict[str, Any]):
        metadata = metadata.copy()
        metadata.update({"category": "personality", "saved_at": now_iso()})
        if self.vector_db_type == "chroma":
            self._upsert_chroma([text], [metadata], ids=[f"personality_{now_iso()}"])
        else:
            self._upsert_faiss([text], [metadata])

    def save_experience_data(self, text: str, metadata: Dict[str, Any]):
        metadata = metadata.copy()
        metadata.update({"category": "experience", "saved_at": now_iso()})
        if self.vector_db_type == "chroma":
            self._upsert_chroma([text], [metadata], ids=[f"experience_{now_iso()}"])
        else:
            self._upsert_faiss([text], [metadata])

    def search_similar(self, query: str, category: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Return list of dicts: [{"id":..., "text":..., "metadata":..., "score":...}, ...]
        """
        q_emb = self.embedding_model.encode([query], show_progress_bar=False)
        if self.vector_db_type == "chroma":
            # Chroma query
            results = self.collection.query(query_embeddings=q_emb, n_results=top_k, include=["metadatas","documents","distances"])
            docs = []
            # `ids` は `include` に指定しなくてもデフォルトで返されるため、後続のコードは変更不要
            for i in range(len(results["ids"])):
                # results return lists per field
                for j in range(len(results["ids"][i])):
                    meta = results["metadatas"][i][j]
                    if category and meta.get("category") != category:
                        continue
                    docs.append({
                        "id": results["ids"][i][j],
                        "text": results["documents"][i][j],
                        "metadata": meta,
                        "score": results["distances"][i][j]
                    })
            return docs[:top_k]
        else:
            # FAISS search - inner product on normalized vectors works as cosine similarity
            qn = self._normalize(q_emb).astype('float32')
            D, I = self.index.search(qn, top_k)
            docs = []
            for idx, score in zip(I[0], D[0]):
                if idx < 0:
                    continue
                # mapping: our stored metadata keys are 1-based incremental ints as strings; we stored in insertion order
                # faiss IndexFlatIP doesn't retain ids; we map by insertion ordinal.
                # Here we compute mapping index -> id_str = str(idx+1)
                id_str = str(idx+1)
                entry = self.metadata.get(id_str)
                if not entry:
                    continue
                if category and entry["meta"].get("category") != category:
                    continue
                docs.append({
                    "id": id_str,
                    "text": entry["text"],
                    "metadata": entry["meta"],
                    "score": float(score)
                })
            return docs

    def persist_chroma(self):
        """
        [DEPRECATED] With PersistentClient, data is persisted automatically.
        This method is kept for backward compatibility but does nothing.
        """
        if self.vector_db_type == "chroma":
            logger.info("Using PersistentClient. Data is automatically persisted, no need to call persist().")