import os

from cti_app.embedding_constants import EMBEDDING_PROVIDER, EMBEDDING_MODEL


def get_embeddings():
    if EMBEDDING_PROVIDER == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model=EMBEDDING_MODEL)

    elif EMBEDDING_PROVIDER == "ollama":
        from langchain_ollama import OllamaEmbeddings
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return OllamaEmbeddings(
            model=EMBEDDING_MODEL,
            base_url=ollama_url
        )

    else:
        raise ValueError(f"Unsupported embedding provider: {EMBEDDING_PROVIDER}")