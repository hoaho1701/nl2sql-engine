"""Generate SQL from a natural-language question via Ollama, using the RAG prompt."""


def generate_sql(question: str) -> str:
    """Retrieve context, build messages, call Ollama (temperature=0), return raw SQL text."""
    raise NotImplementedError
