"""Giai đoạn 6 — vòng tự sửa lỗi (self-correction loop).

Xem PROGRESS.md Giai đoạn 6: log lại từng lượt thử, giới hạn max_retries
để tránh lặp vô hạn / chờ lâu.
"""


def answer_question(question: str, max_retries: int = 2):
    """TODO: generate_sql(question) -> run_sql_safe(sql); nếu lỗi thực thi, gửi
    lại (câu hỏi gốc, sql vừa sai, thông báo lỗi) cho LLM sửa, thử lại tối đa
    max_retries lần. Log lại từng lượt (question, sql, lỗi nếu có, số lần retry)."""
    raise NotImplementedError
