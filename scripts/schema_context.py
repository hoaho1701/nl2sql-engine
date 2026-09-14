"""Giai đoạn 2 — Schema metadata layer.

Sinh DDL + mô tả nghiệp vụ + cảnh báo bẫy (fan-out, NULL) — nguyên liệu
thô cho vector store ở Giai đoạn 3. Xem PROGRESS.md Giai đoạn 2.
"""


def generate_ddl(engine) -> list[str]:
    """TODO: dùng sqlalchemy.inspect(engine) sinh CREATE TABLE cho từng bảng, gồm FK thật."""
    raise NotImplementedError


TABLE_DESCRIPTIONS = {
    # TODO: mô tả nghiệp vụ từng bảng, liệt kê đủ giá trị enum thật (order_status,
    # payment_type, review_score...), ghi chú ý nghĩa của NULL nếu có.
}

NON_UNIQUE_PARENT_KEYS = {
    # TODO: cột JOIN không unique đã tự phát hiện bằng cách đếm cardinality
    # (vd geolocation.geolocation_zip_code_prefix) — cảnh báo rủi ro fan-out.
}

NULLABLE_CHILD_KEYS = {
    # TODO: cột FK có thể NULL — cảnh báo rủi ro INNER JOIN âm thầm loại dòng.
}


def build_documentation_chunks() -> list[str]:
    """TODO: chuyển TABLE_DESCRIPTIONS/NON_UNIQUE_PARENT_KEYS/NULLABLE_CHILD_KEYS
    thành list đoạn văn bản độc lập — mỗi phần tử sẽ được embed riêng ở Giai đoạn 3."""
    raise NotImplementedError
