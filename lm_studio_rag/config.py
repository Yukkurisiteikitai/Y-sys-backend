# config.py
import os

# LM Studio OpenAI互換 API 設定
LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234")  # 例: http://localhost:8080
LM_STUDIO_API_KEY = os.getenv("LM_STUDIO_API_KEY", "your_api_key_here")

# Embedding model to use for sentence-transformers
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

# Vector DB config
VECTOR_DB_TYPE = os.getenv("VECTOR_DB_TYPE", "chroma")  # "chroma" or "faiss"
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "./faiss.index")
METADATA_STORE_PATH = os.getenv("METADATA_STORE_PATH", "./faiss_metadata.json")

# Other
DEFAULT_EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 -> 384
