"""Giai đoạn 4 — gọi Ollama sinh SQL từ câu hỏi, dùng RAG prompt động.

Xem PROGRESS.md Giai đoạn 4: temperature=0 bắt buộc, raw SQL text trả về
chưa "làm sạch" markdown/code fence — xử lý việc đó ở Giai đoạn 5.
"""


def generate_sql(question: str) -> str:
    """TODO: vector_store.retrieve(question) -> build_prompt.build_messages(...)
    -> gọi Ollama qua SDK openai (base_url=OLLAMA_BASE_URL, temperature=0)
    -> trả response.choices[0].message.content."""
    raise NotImplementedError
