"""Build a dynamic RAG prompt from retrieved context."""


def build_messages(question: str, context: str) -> list[dict]:
    """Format retrieved context + question into OpenAI chat-format messages."""
    raise NotImplementedError
