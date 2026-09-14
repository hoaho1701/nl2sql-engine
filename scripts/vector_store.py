"""Giai đoạn 3 — Vector store & training data cho RAG.

ChromaDB local (3 collection: ddl, documentation, sql_examples) + Ollama
embedding model. Xem PROGRESS.md Giai đoạn 3, đặc biệt cảnh báo data
leakage: KHÔNG add case từ eval_test_set.py vào sql_examples.
"""


def get_chroma_client():
    """TODO: chromadb.PersistentClient(path=CHROMA_PERSIST_DIR), tạo/lấy 3 collection
    (ddl, documentation, sql_examples)."""
    raise NotImplementedError


def embed(text: str) -> list[float]:
    """TODO: gọi Ollama embedding endpoint (model nomic-embed-text) cho 1 đoạn text."""
    raise NotImplementedError


def add_ddl(text: str) -> None:
    """TODO: embed + add vào collection ddl."""
    raise NotImplementedError


def add_documentation(text: str) -> None:
    """TODO: embed + add vào collection documentation."""
    raise NotImplementedError


def add_sql_example(question: str, sql: str) -> None:
    """TODO: embed câu hỏi + add (question, sql) vào collection sql_examples."""
    raise NotImplementedError


def retrieve(question: str, k_ddl: int = 5, k_doc: int = 3, k_examples: int = 3) -> str:
    """TODO: embed câu hỏi, query top-k mỗi collection, ghép thành 1 context string
    để đưa vào build_prompt.build_messages()."""
    raise NotImplementedError
