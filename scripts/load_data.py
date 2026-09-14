from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

DATA_DIR = Path("data/raw")
DB_PATH = Path("data/olist.db")

# Map CSV filename -> table name in the database
TABLE_NAME_MAP = {
    "olist_customers_dataset.csv": "customers",
    "olist_geolocation_dataset.csv": "geolocation",
    "olist_order_items_dataset.csv": "order_items",
    "olist_order_payments_dataset.csv": "order_payments",
    "olist_order_reviews_dataset.csv": "order_reviews",
    "olist_orders_dataset.csv": "orders",
    "olist_products_dataset.csv": "products",
    "olist_sellers_dataset.csv": "sellers",
    "product_category_name_translation.csv": "product_category_name_translation",
}

# Explicit per-table list of date columns, checked by hand against each CSV's
# header. Deliberately not inferred from column names (e.g. via a "date"/
# "timestamp" keyword match): keyword matching both misses real date columns
# with unrelated names (e.g. "order_approved_at") and can false-positive on
# unrelated columns whose name happens to contain the keyword as a substring.
DATE_COLUMN_BY_TABLE = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "order_items": [
        "shipping_limit_date",
    ],
    "order_reviews": [
        "review_creation_date",
        "review_answer_timestamp",
    ],
}

def convert_date_columns(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    # errors="coerce" turns unparseable values into NaT instead of raising,
    # which is safe here since the columns listed above are known to be dates.
    for col in DATE_COLUMN_BY_TABLE.get(table_name, []):
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def load_csv_to_table(path: Path, engine) -> None:
    table_name = TABLE_NAME_MAP.get(path.name)
    if table_name is None:
        raise ValueError(f"No table mapping defined for {path.name}")

    df = pd.read_csv(path)
    df = convert_date_columns(df, table_name)

    # if_exists="replace": drop and recreate the table each run, so
    # re-running this script during development always starts from a clean state.
    df.to_sql(table_name, engine, if_exists="replace", index=False)
    print(f"Loaded {table_name}: {len(df):,} rows, {len(df.columns)} columns")


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{DB_PATH}")

    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {DATA_DIR.resolve()}")

    for path in csv_files:
        load_csv_to_table(path, engine)

    print(f"\nDone. Database written to {DB_PATH.resolve()}")


if __name__ == "__main__":
    main()
