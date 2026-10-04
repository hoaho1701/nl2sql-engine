"""Chroma-backed vector store for RAG: ddl, documentation, and sql_examples collections."""

import hashlib
import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from openai import OpenAI


REPO_ROOT = Path(__file__).resolve().parent.parent

# Default number of matches taken from each collection. Measured on the Olist schema:
# the 9 DDL statements total only 2,845 characters and some questions need tables whose
# names the question never mentions (k_ddl=5 still misses geolocation for a distance
# question), so all of them are included. With k_doc=3, 3 of 8 probe questions missed the
# documentation chunk they depend on; k_doc=5 found all 8. Prompt size stays near 1,200 tokens.
DEFAULT_K_DDL = 9
DEFAULT_K_DOC = 5
DEFAULT_K_EXAMPLES = 3


def _persist_path() -> str:
    """Where the Chroma store lives: CHROMA_PERSIST_DIR from .env, relative to the repo root."""
    load_dotenv(REPO_ROOT / ".env")
    return str(REPO_ROOT / os.environ["CHROMA_PERSIST_DIR"])


def get_chroma_client():
    """Open the persistent Chroma store and return its 3 collections as a dict.

    Keys: "ddl", "documentation", "sql_examples". Each collection uses cosine distance.
    """
    client = chromadb.PersistentClient(path=_persist_path())
    return {
        name: client.get_or_create_collection(
            name,
            configuration={"hnsw": {"space": "cosine"}},
        )
        for name in ("ddl", "documentation", "sql_examples")
    }


def _get_client() -> OpenAI:
    """OpenAI SDK client pointed at the local Ollama server."""
    load_dotenv()
    # Ollama ignores the API key, but the SDK refuses to start without one.
    return OpenAI(base_url=os.environ["OLLAMA_BASE_URL"], api_key="ollama")


def embed_many(texts: list[str]) -> list[list[float]]:
    """Embed several texts in a single request; vectors come back in the input order."""
    if not texts:
        # Ollama rejects an empty input list with a 400 error.
        return []
    response = _get_client().embeddings.create(
        model=os.environ["OLLAMA_EMBED_MODEL"],
        input=texts,
    )
    # Sort by the index the server reports instead of trusting the response order.
    return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]


def embed(text: str) -> list[float]:
    """Call the Ollama embedding endpoint (nomic-embed-text) for one chunk of text."""
    return embed_many([text])[0]


def make_id(text: str) -> str:
    """Stable id for a piece of text: the same text always maps to the same id."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def add_ddl(text: str) -> None:
    collections = get_chroma_client()
    collections["ddl"].upsert(
        ids=[make_id(text)],
        documents=[text],
        embeddings=[embed(text)],
    )


def add_documentation(text: str) -> None:
    collections = get_chroma_client()
    collections["documentation"].upsert(
        ids=[make_id(text)],
        documents=[text],
        embeddings=[embed(text)],
    )


def add_sql_example(question: str, sql: str) -> None:
    collections = get_chroma_client()
    collections["sql_examples"].upsert(
        ids=[make_id(question)],
        documents=[question],
        embeddings=[embed(question)],
        metadatas=[{"sql": sql}],
    )


def format_context(parts: dict) -> str:
    """Render retrieved parts as the context text that goes into the LLM prompt.

    Sections with nothing in them are left out entirely.
    """
    sections = []
    if parts["ddl"]:
        sections.append("### Database schema (DDL)\n" + "\n\n".join(parts["ddl"]))
    if parts["documentation"]:
        notes = "\n".join(f"- {note}" for note in parts["documentation"])
        sections.append("### Documentation\n" + notes)
    if parts["examples"]:
        blocks = [f"Question: {ex['question']}\nSQL: {ex['sql']}" for ex in parts["examples"]]
        sections.append("### Example questions and SQL\n" + "\n\n".join(blocks))
    return "\n\n".join(sections)


def retrieve_parts(
    question: str,
    k_ddl: int = DEFAULT_K_DDL,
    k_doc: int = DEFAULT_K_DOC,
    k_examples: int = DEFAULT_K_EXAMPLES,
) -> dict:
    """Embed the question once and return the top-k matches from each collection.

    Returns {"ddl": [str], "documentation": [str], "examples": [{"question", "sql"}]},
    most similar first.
    """
    collections = get_chroma_client()
    vector = embed(question)

    def top(name, k):
        if k <= 0:
            return {"documents": [[]], "metadatas": [[]]}
        return collections[name].query(query_embeddings=[vector], n_results=k)

    ddl = top("ddl", k_ddl)["documents"][0]
    doc = top("documentation", k_doc)["documents"][0]
    ex = top("sql_examples", k_examples)
    examples = [
        {"question": q, "sql": m["sql"]}
        for q, m in zip(ex["documents"][0], ex["metadatas"][0])
    ]
    return {"ddl": ddl, "documentation": doc, "examples": examples}


def retrieve(
    question: str,
    k_ddl: int = DEFAULT_K_DDL,
    k_doc: int = DEFAULT_K_DOC,
    k_examples: int = DEFAULT_K_EXAMPLES,
) -> str:
    """Embed the question, query top-k from each collection, merge into one context string."""
    return format_context(retrieve_parts(question, k_ddl, k_doc, k_examples))


def reset_store() -> None:
    """Delete the three collections so the next get_chroma_client() starts empty."""
    client = chromadb.PersistentClient(path=_persist_path())
    existing = [collection.name for collection in client.list_collections()]
    for name in ("ddl", "documentation", "sql_examples"):
        if name in existing:
            client.delete_collection(name)


def seed(ddl_statements, documentation_chunks, examples) -> dict:
    """Rebuild the store from scratch and return how many entries each collection holds."""
    reset_store()
    for statement in ddl_statements:
        add_ddl(statement)
    for chunk in documentation_chunks:
        add_documentation(chunk)
    for example in examples:
        add_sql_example(example["question"], example["sql"])
    collections = get_chroma_client()
    return {name: collection.count() for name, collection in collections.items()}


def main() -> None:
    """Load the real schema, documentation and training examples into the store."""
    from app.load_data import get_engine
    from app.schema_context import build_documentation_chunks, generate_ddl
    from app.training_examples import TRAINING_EXAMPLES

    counts = seed(generate_ddl(get_engine()), build_documentation_chunks(), TRAINING_EXAMPLES)
    for name, count in counts.items():
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()
