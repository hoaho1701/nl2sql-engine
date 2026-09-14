"""Chroma-backed vector store for RAG: ddl, documentation, and sql_examples collections."""


def get_chroma_client():
    """chromadb.PersistentClient(path=CHROMA_PERSIST_DIR); create/get the 3 collections."""
    raise NotImplementedError


def embed(text: str) -> list[float]:
    """Call the Ollama embedding endpoint (nomic-embed-text) for one chunk of text."""
    raise NotImplementedError


def add_ddl(text: str) -> None:
    raise NotImplementedError


def add_documentation(text: str) -> None:
    raise NotImplementedError


def add_sql_example(question: str, sql: str) -> None:
    raise NotImplementedError


def retrieve(question: str, k_ddl: int = 5, k_doc: int = 3, k_examples: int = 3) -> str:
    """Embed the question, query top-k from each collection, merge into one context string."""
    raise NotImplementedError
