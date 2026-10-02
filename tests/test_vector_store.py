"""Tests for vector_store, written one step at a time (see the section markers)."""

import urllib.request
from types import SimpleNamespace

import pytest

from app import vector_store


def _ollama_is_up() -> bool:
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=1)
        return True
    except OSError:
        return False


# --------------------------------------------------------------------------
# Step 1: embed / embed_many
# --------------------------------------------------------------------------


class FakeEmbeddings:
    """Stand-in for client.embeddings: vector = [len(text), position in the request]."""

    def __init__(self, reverse_response=False):
        self.calls = []
        self.reverse_response = reverse_response

    def create(self, model, input):
        self.calls.append({"model": model, "input": list(input)})
        data = [
            SimpleNamespace(index=i, embedding=[float(len(text)), float(i)])
            for i, text in enumerate(input)
        ]
        if self.reverse_response:
            data.reverse()
        return SimpleNamespace(data=data)


@pytest.fixture
def fake_embeddings(monkeypatch):
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "test-model")
    fake = FakeEmbeddings()
    monkeypatch.setattr(vector_store, "_get_client", lambda: SimpleNamespace(embeddings=fake))
    return fake


def test_embed_returns_the_vector_of_one_text(fake_embeddings):
    assert vector_store.embed("abc") == [3.0, 0.0]


def test_embed_many_returns_vectors_in_input_order(fake_embeddings):
    assert vector_store.embed_many(["a", "abc"]) == [[1.0, 0.0], [3.0, 1.0]]


def test_embed_many_sends_a_single_request(fake_embeddings):
    vector_store.embed_many(["a", "b", "c"])
    assert len(fake_embeddings.calls) == 1
    assert fake_embeddings.calls[0]["input"] == ["a", "b", "c"]


def test_embed_many_uses_the_model_from_the_environment(fake_embeddings):
    vector_store.embed_many(["a"])
    assert fake_embeddings.calls[0]["model"] == "test-model"


def test_embed_many_of_nothing_makes_no_request(fake_embeddings):
    assert vector_store.embed_many([]) == []
    assert fake_embeddings.calls == []


def test_embed_many_restores_order_when_the_server_reorders(monkeypatch):
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "test-model")
    fake = FakeEmbeddings(reverse_response=True)
    monkeypatch.setattr(vector_store, "_get_client", lambda: SimpleNamespace(embeddings=fake))
    assert vector_store.embed_many(["a", "abc"]) == [[1.0, 0.0], [3.0, 1.0]]


@pytest.mark.skipif(not _ollama_is_up(), reason="Ollama is not running")
def test_embed_with_real_ollama_returns_768_dimensions():
    vector = vector_store.embed("How many orders are there?")
    assert len(vector) == 768
    assert all(isinstance(value, float) for value in vector)


# --------------------------------------------------------------------------
# Step 2: get_chroma_client (YOUR TURN — these tests start red)
# --------------------------------------------------------------------------


@pytest.fixture
def chroma_dir(tmp_path, monkeypatch):
    path = tmp_path / "chroma"
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(path))
    return path


def test_get_chroma_client_returns_the_three_collections(chroma_dir):
    collections = vector_store.get_chroma_client()
    assert set(collections) == {"ddl", "documentation", "sql_examples"}


def test_collections_start_empty(chroma_dir):
    collections = vector_store.get_chroma_client()
    assert all(collection.count() == 0 for collection in collections.values())


def test_collections_use_cosine_distance(chroma_dir):
    collections = vector_store.get_chroma_client()
    for collection in collections.values():
        assert collection.configuration["hnsw"]["space"] == "cosine"


def test_collections_are_persisted_on_disk(chroma_dir):
    first = vector_store.get_chroma_client()
    first["ddl"].upsert(ids=["a"], documents=["x"], embeddings=[[1.0, 0.0]])
    second = vector_store.get_chroma_client()
    assert second["ddl"].count() == 1


# --------------------------------------------------------------------------
# Step 3: make_id, add_ddl, add_documentation, add_sql_example
# --------------------------------------------------------------------------

VOCAB = ["order", "seller", "payment", "review", "customer"]


def fake_embed(text):
    """Keyword-count vector: texts that mention the same words end up close together."""
    lowered = text.lower()
    # The constant 0.1 keeps the vector from being all zeros (cosine is undefined for it).
    return [float(lowered.count(word)) for word in VOCAB] + [0.1]


@pytest.fixture
def store(chroma_dir, monkeypatch):
    """A temporary Chroma store with embed() replaced by the keyword-count fake."""
    monkeypatch.setattr(vector_store, "embed", fake_embed)
    return vector_store.get_chroma_client


def test_make_id_is_deterministic():
    assert vector_store.make_id("CREATE TABLE orders") == vector_store.make_id("CREATE TABLE orders")


def test_make_id_differs_for_different_text():
    assert vector_store.make_id("orders") != vector_store.make_id("sellers")


def test_make_id_is_16_hex_characters():
    value = vector_store.make_id("anything")
    assert len(value) == 16
    assert all(char in "0123456789abcdef" for char in value)


def test_add_ddl_stores_the_text_in_the_ddl_collection(store):
    vector_store.add_ddl("CREATE TABLE orders (order_id TEXT)")
    collections = store()
    assert collections["ddl"].get()["documents"] == ["CREATE TABLE orders (order_id TEXT)"]


def test_add_ddl_leaves_the_other_collections_empty(store):
    vector_store.add_ddl("CREATE TABLE orders (order_id TEXT)")
    collections = store()
    assert collections["documentation"].count() == 0
    assert collections["sql_examples"].count() == 0


def test_add_ddl_twice_with_the_same_text_keeps_one_entry(store):
    vector_store.add_ddl("CREATE TABLE orders (order_id TEXT)")
    vector_store.add_ddl("CREATE TABLE orders (order_id TEXT)")
    assert store()["ddl"].count() == 1


def test_add_ddl_stores_the_embedding_of_the_text(store):
    text = "CREATE TABLE orders (order_id TEXT)"
    vector_store.add_ddl(text)
    stored = store()["ddl"].get(include=["embeddings"])["embeddings"][0]
    assert list(stored) == pytest.approx(fake_embed(text))


def test_add_documentation_goes_to_the_documentation_collection(store):
    vector_store.add_documentation("Table sellers: one row per seller.")
    collections = store()
    assert collections["documentation"].get()["documents"] == ["Table sellers: one row per seller."]
    assert collections["ddl"].count() == 0


def test_add_documentation_twice_keeps_one_entry(store):
    vector_store.add_documentation("Table sellers: one row per seller.")
    vector_store.add_documentation("Table sellers: one row per seller.")
    assert store()["documentation"].count() == 1


def test_add_sql_example_stores_the_question_as_the_document(store):
    vector_store.add_sql_example("How many orders?", "SELECT COUNT(*) FROM orders")
    assert store()["sql_examples"].get()["documents"] == ["How many orders?"]


def test_add_sql_example_stores_the_sql_in_metadata(store):
    vector_store.add_sql_example("How many orders?", "SELECT COUNT(*) FROM orders")
    metadatas = store()["sql_examples"].get()["metadatas"]
    assert metadatas == [{"sql": "SELECT COUNT(*) FROM orders"}]


def test_add_sql_example_embeds_the_question_not_the_sql(store):
    vector_store.add_sql_example("How many orders?", "SELECT COUNT(*) FROM sellers")
    stored = store()["sql_examples"].get(include=["embeddings"])["embeddings"][0]
    assert list(stored) == pytest.approx(fake_embed("How many orders?"))


def test_add_sql_example_with_the_same_question_replaces_the_sql(store):
    vector_store.add_sql_example("How many orders?", "SELECT 1")
    vector_store.add_sql_example("How many orders?", "SELECT COUNT(*) FROM orders")
    collection = store()["sql_examples"]
    assert collection.count() == 1
    assert collection.get()["metadatas"] == [{"sql": "SELECT COUNT(*) FROM orders"}]


# --------------------------------------------------------------------------
# Step 4: format_context, retrieve_parts, retrieve
# --------------------------------------------------------------------------

DDL_ORDERS = "CREATE TABLE orders (order_id TEXT)"
DDL_SELLERS = "CREATE TABLE sellers (seller_id TEXT, seller_state TEXT)"
DDL_PAYMENTS = "CREATE TABLE order_payments (payment_type TEXT, payment_value NUMERIC)"
DOC_ORDERS = "Table orders: one row per order."
DOC_SELLERS = "Table sellers: one row per seller."
EXAMPLE_ORDERS = ("How many orders are there?", "SELECT COUNT(*) FROM orders")
EXAMPLE_SELLERS = ("How many sellers are there?", "SELECT COUNT(*) FROM sellers")

PARTS = {
    "ddl": [DDL_SELLERS, DDL_ORDERS],
    "documentation": [DOC_SELLERS],
    "examples": [{"question": EXAMPLE_SELLERS[0], "sql": EXAMPLE_SELLERS[1]}],
}


@pytest.fixture
def seeded(store):
    """The fake-embedding store filled with a few ddl, documentation and example entries."""
    for ddl in (DDL_ORDERS, DDL_SELLERS, DDL_PAYMENTS):
        vector_store.add_ddl(ddl)
    for doc in (DOC_ORDERS, DOC_SELLERS):
        vector_store.add_documentation(doc)
    for question, sql in (EXAMPLE_ORDERS, EXAMPLE_SELLERS):
        vector_store.add_sql_example(question, sql)
    return store


def test_format_context_contains_every_part():
    text = vector_store.format_context(PARTS)
    for expected in (DDL_SELLERS, DDL_ORDERS, DOC_SELLERS, EXAMPLE_SELLERS[0], EXAMPLE_SELLERS[1]):
        assert expected in text


def test_format_context_orders_schema_then_documentation_then_examples():
    text = vector_store.format_context(PARTS)
    assert text.index(DDL_SELLERS) < text.index(DOC_SELLERS) < text.index(EXAMPLE_SELLERS[0])


def test_format_context_keeps_the_retrieval_order_within_a_section():
    text = vector_store.format_context(PARTS)
    assert text.index(DDL_SELLERS) < text.index(DDL_ORDERS)


def test_format_context_leaves_out_empty_sections():
    text = vector_store.format_context({"ddl": [DDL_ORDERS], "documentation": [], "examples": []})
    assert DDL_ORDERS in text
    assert "Documentation" not in text
    assert "Example" not in text


def test_format_context_of_nothing_is_an_empty_string():
    assert vector_store.format_context({"ddl": [], "documentation": [], "examples": []}) == ""


def test_retrieve_parts_returns_the_three_parts(seeded):
    parts = vector_store.retrieve_parts("How many sellers are there?")
    assert set(parts) == {"ddl", "documentation", "examples"}


def test_retrieve_parts_puts_the_most_similar_ddl_first(seeded):
    parts = vector_store.retrieve_parts("How many sellers are there?")
    assert parts["ddl"][0] == DDL_SELLERS


def test_retrieve_parts_puts_the_most_similar_documentation_first(seeded):
    parts = vector_store.retrieve_parts("How many orders are there?")
    assert parts["documentation"][0] == DOC_ORDERS


def test_retrieve_parts_returns_examples_with_question_and_sql(seeded):
    parts = vector_store.retrieve_parts("How many sellers are there?", k_examples=1)
    assert parts["examples"] == [{"question": EXAMPLE_SELLERS[0], "sql": EXAMPLE_SELLERS[1]}]


def test_retrieve_parts_respects_k(seeded):
    parts = vector_store.retrieve_parts("orders", k_ddl=1, k_doc=1, k_examples=1)
    assert len(parts["ddl"]) == 1
    assert len(parts["documentation"]) == 1
    assert len(parts["examples"]) == 1


def test_retrieve_parts_with_k_larger_than_the_collection_returns_everything(seeded):
    parts = vector_store.retrieve_parts("orders", k_ddl=50, k_doc=50, k_examples=50)
    assert len(parts["ddl"]) == 3
    assert len(parts["documentation"]) == 2
    assert len(parts["examples"]) == 2


def test_retrieve_parts_with_k_zero_skips_that_part(seeded):
    # Chroma raises a TypeError for n_results=0, so zero has to be handled by the caller.
    parts = vector_store.retrieve_parts("orders", k_ddl=0, k_doc=0, k_examples=0)
    assert parts == {"ddl": [], "documentation": [], "examples": []}


def test_retrieve_parts_on_an_empty_store_returns_empty_parts(store):
    parts = vector_store.retrieve_parts("How many orders are there?")
    assert parts == {"ddl": [], "documentation": [], "examples": []}


def test_retrieve_parts_embeds_the_question_only_once(seeded, monkeypatch):
    calls = []

    def counting_embed(text):
        calls.append(text)
        return fake_embed(text)

    monkeypatch.setattr(vector_store, "embed", counting_embed)
    vector_store.retrieve_parts("How many orders are there?")
    assert calls == ["How many orders are there?"]


def test_retrieve_returns_the_formatted_parts(seeded):
    question = "How many sellers are there?"
    parts = vector_store.retrieve_parts(question)
    assert vector_store.retrieve(question) == vector_store.format_context(parts)


def test_retrieve_passes_the_k_values_through(seeded):
    text = vector_store.retrieve("How many sellers are there?", k_ddl=1, k_doc=1, k_examples=1)
    assert DDL_SELLERS in text
    assert DDL_ORDERS not in text and DDL_PAYMENTS not in text
