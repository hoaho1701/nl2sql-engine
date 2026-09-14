"""Giai đoạn 7 — bộ eval (question, gold_sql).

⚠️ KHÔNG add case nào từ đây vào vector_store (Giai đoạn 3) — dùng riêng để ĐO.
Checklist dạng câu hỏi cần phủ: xem PROGRESS.md Giai đoạn 7.
"""

EVAL_CASES = [
    # TODO: tối thiểu 15 cặp (question, gold_sql), mỗi phần tử dạng:
    # {"question": "...", "gold_sql": "..."}
    # Phủ đủ: đếm đơn giản, JOIN + AVG, GROUP BY + top-1, bẫy NULL, bẫy fan-out,
    # HAVING qua subquery, tổng nhiều cột, filter theo ngày, GROUP BY tìm max,
    # so sánh 2 cột ngày, JOIN từ 3 bảng trở lên, và vài câu trả về NHIỀU DÒNG thật.
]
