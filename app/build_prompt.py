"""Build a dynamic RAG prompt from retrieved context."""

SYSTEM_PROMPT_TEMPLATE = """You are a SQL expert. Given the database schema, \
documentation, and example question/SQL pairs below, write a single \
PostgreSQL SELECT statement that answers the user's question.
Return ONLY the raw SQL — no explanation, no markdown, no code fences.

{context}"""


def build_messages(question: str, context: str) -> list[dict]:
    """Format retrieved context + question into OpenAI chat-format messages."""
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]
