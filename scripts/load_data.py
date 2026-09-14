"""Giai đoạn 1 — Nền dữ liệu (Postgres).

Load 9 CSV Olist vào Postgres với FK thật. Xem PROGRESS.md Giai đoạn 1
cho danh sách 9 quan hệ FK và lý do tách bước tạo DDL / nạp dữ liệu.
"""

TABLE_NAME_MAP = {
    # TODO: map tên file CSV -> tên bảng, vd "olist_customers_dataset.csv": "customers"
}

DATE_COLUMN_BY_TABLE = {
    # TODO: khai tường minh cột ngày tháng theo từng bảng (không đoán qua keyword tên cột)
}


def get_engine():
    """TODO: sqlalchemy.create_engine(...) trỏ Postgres, đọc connection info từ .env."""
    raise NotImplementedError


def create_schema(engine) -> None:
    """TODO: chạy DDL tạo 9 bảng với FK thật, đúng thứ tự phụ thuộc (bảng cha trước bảng con)."""
    raise NotImplementedError


def load_csv_to_table(engine, csv_path: str, table_name: str) -> None:
    """TODO: đọc CSV, convert đúng cột ngày tháng sang datetime, to_sql(..., if_exists="append")."""
    raise NotImplementedError


def verify_row_counts(engine) -> None:
    """TODO: so len(df) mỗi CSV với SELECT COUNT(*) tương ứng trong Postgres."""
    raise NotImplementedError


def main() -> None:
    """TODO: create_schema -> load_csv_to_table cho cả 9 bảng -> verify_row_counts."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
