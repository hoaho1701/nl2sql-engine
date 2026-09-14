"""Giai đoạn 1 — khám phá dữ liệu Olist trước khi load.

Mục đích: tự phát hiện cột nào là ngày tháng, cột nào là enum, tỉ lệ NULL,
cardinality — không đoán qua tên cột. Xem PROGRESS.md Giai đoạn 1.
"""


def inspect_csv(csv_path: str) -> None:
    """TODO: đọc CSV bằng pandas, in dtype mỗi cột, cardinality, tỉ lệ NULL, vài dòng mẫu."""
    raise NotImplementedError


def main() -> None:
    """TODO: chạy inspect_csv cho cả 9 file trong data/raw/."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
