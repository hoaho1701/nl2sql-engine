"""Generate SQL from a natural-language question via Ollama, using the RAG prompt."""

import os

from dotenv import load_dotenv
from openai import OpenAI

from app.build_prompt import build_messages
from app.vector_store import REPO_ROOT, retrieve


def _get_client() -> OpenAI:
    """OpenAI SDK client pointed at the local Ollama server."""
    load_dotenv(REPO_ROOT / ".env")
    return OpenAI(base_url=os.environ["OLLAMA_BASE_URL"], api_key="ollama", timeout=120)


def generate_sql(question: str) -> str:
    """Retrieve context, build messages, call Ollama (temperature=0), return raw SQL text."""
    messages = build_messages(question, retrieve(question))
    response = _get_client().chat.completions.create(
        model=os.environ["OLLAMA_SQL_MODEL"],
        messages=messages,
        temperature=0,
    )
    return response.choices[0].message.content
