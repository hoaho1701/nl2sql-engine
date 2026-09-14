"""Giai đoạn 7 — đo execution accuracy.

So kết quả (Counter-based, KHÔNG so text SQL) — xem PROGRESS.md Giai đoạn 7
cho các lỗi thường gặp khi viết vòng lặp này (UnboundLocalError, biến cờ
reset sai vị trí, gõ nhầm biến đếm).
"""

from collections import Counter


def normalize_result(rows, expected_column_count: int | None = None) -> Counter:
    """TODO: chuẩn hoá kết quả trả về (vd cắt cột thừa nếu predicted có thêm cột)
    trước khi đưa vào Counter để so sánh."""
    raise NotImplementedError


def evaluate(use_self_correction: bool = False) -> None:
    """TODO: với mỗi case trong eval_test_set.EVAL_CASES — chạy generate_sql (hoặc
    self_correct.answer_question nếu use_self_correction=True) + run_sql_safe cho
    cả predicted và gold_sql, so bằng Counter (qua normalize_result), in báo cáo.
    Bọc try/except từng case — lỗi thực thi SQL predicted tính là sai, không crash."""
    raise NotImplementedError


if __name__ == "__main__":
    evaluate()
