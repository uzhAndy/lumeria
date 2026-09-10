import os
from django.conf import settings

COLLECTION_NAME = "mitre_campaigns"

# VECTOR_STORE_DIR = os.path.join(settings.BASE_DIR, "data/chroma")
VECTOR_STORE_LOCALLY = os.path.join(settings.BASE_DIR, "chroma")
VECTOR_STORE_DIR = os.getenv("VECTOR_STORE_DIR", VECTOR_STORE_LOCALLY)

# bge-large (good semantic + relational understanding)
EMBEDDING_PROVIDER = "ollama"
EMBEDDING_MODEL = "embeddinggemma"
DOC_PREFIX = ""

# qwen (is running too slow)
# EMBEDDING_MODEL = "qwen3-embedding:8b" # (used ollama pull qwen3-embedding:8b)
# EMBEDDING_PROVIDER = "ollama"
# DOC_PREFIX = ""

# nomic-embed-text (fast enough)
# EMBEDDING_MODEL = "nomic-embed-text"
# EMBEDDING_PROVIDER = "ollama"
# DOC_PREFIX = "search_document:" # should improve embeddings for nomic-embed-text model

# openai model (is running too slow):
# VECTOR_STORE_DIR = os.path.join(settings.BASE_DIR, "data/vector_store_db_openai")
# EMBEDDING_PROVIDER = "openai"
# EMBEDDING_MODEL = "text-embedding-3-small"  # or text-embedding-3-large (but is much slower)
# DOC_PREFIX = "" # no prefix needed for openai model (can even hurt)