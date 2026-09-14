"""Giai đoạn 4 — build prompt RAG động từ context đã retrieve.

Xem PROGRESS.md Giai đoạn 4: system = luật chung + DDL/doc liên quan;
user = few-shot examples + câu hỏi thật, examples đặt gần câu hỏi thật.
"""


def build_messages(question: str, context: str) -> list[dict]:
    """TODO: format context (đã retrieve từ vector_store.retrieve) thành messages
    list chuẩn OpenAI chat format ([{"role": "system", ...}, {"role": "user", ...}])."""
    raise NotImplementedError
