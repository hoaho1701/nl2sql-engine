"""Load the 9 Olist CSVs into Postgres with real foreign keys."""

import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from app.inspect_data import RAW_DATA_DIR

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

# Explicit per-table date columns, confirmed by reading inspect_data.py's sample
# rows — not guessed from column names (e.g. order_approved_at has no "date"/
# "timestamp" in its name but is one; other tables have none at all).
DATE_COLUMN_BY_TABLE = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "order_items": ["shipping_limit_date"],
    "order_reviews": ["review_creation_date", "review_answer_timestamp"],
}

# Columns that are whole numbers but contain NULLs, so pandas reads them as float.
# Cast to nullable Int64 before inserting into INTEGER columns.
NULLABLE_INT_COLUMNS_BY_TABLE = {
    "products": [
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ],
}

CHUNK_SIZE = 10_000

# (table_name, CREATE TABLE statement), ordered parents-first so FKs can resolve.
# Not enforced as FKs, on purpose (verified against the real data):
#   - customers/sellers zip -> geolocation: geolocation_zip_code_prefix is not
#     unique (a FK target must be), and some customer/seller zips are missing there.
#   - products.product_category_name -> translation: 2 categories used by products
#     (pc_gamer, portateis_cozinha_e_preparadores_de_alimentos) are not in it.
# Column names are kept exactly as in the CSVs, including the "lenght" typo.
SCHEMA_DDL = [
    (
        "customers",
        """
        CREATE TABLE customers (
            customer_id              TEXT PRIMARY KEY,
            customer_unique_id       TEXT NOT NULL,
            customer_zip_code_prefix INTEGER NOT NULL,
            customer_city            TEXT,
            customer_state           TEXT
        )
        """,
    ),
    (
        "sellers",
        """
        CREATE TABLE sellers (
            seller_id              TEXT PRIMARY KEY,
            seller_zip_code_prefix INTEGER NOT NULL,
            seller_city            TEXT,
            seller_state           TEXT
        )
        """,
    ),
    (
        "product_category_name_translation",
        """
        CREATE TABLE product_category_name_translation (
            product_category_name         TEXT PRIMARY KEY,
            product_category_name_english TEXT NOT NULL
        )
        """,
    ),
    (
        # No natural key: many rows share the same zip prefix.
        "geolocation",
        """
        CREATE TABLE geolocation (
            geolocation_zip_code_prefix INTEGER NOT NULL,
            geolocation_lat             DOUBLE PRECISION,
            geolocation_lng             DOUBLE PRECISION,
            geolocation_city            TEXT,
            geolocation_state           TEXT
        )
        """,
    ),
    (
        "products",
        """
        CREATE TABLE products (
            product_id                 TEXT PRIMARY KEY,
            product_category_name      TEXT,
            product_name_lenght        INTEGER,
            product_description_lenght INTEGER,
            product_photos_qty         INTEGER,
            product_weight_g           INTEGER,
            product_length_cm          INTEGER,
            product_height_cm          INTEGER,
            product_width_cm           INTEGER
        )
        """,
    ),
    (
        "orders",
        """
        CREATE TABLE orders (
            order_id                      TEXT PRIMARY KEY,
            customer_id                   TEXT NOT NULL REFERENCES customers (customer_id),
            order_status                  TEXT NOT NULL,
            order_purchase_timestamp      TIMESTAMP,
            order_approved_at             TIMESTAMP,
            order_delivered_carrier_date  TIMESTAMP,
            order_delivered_customer_date TIMESTAMP,
            order_estimated_delivery_date TIMESTAMP
        )
        """,
    ),
    (
        "order_items",
        """
        CREATE TABLE order_items (
            order_id            TEXT NOT NULL REFERENCES orders (order_id),
            order_item_id       INTEGER NOT NULL,
            product_id          TEXT NOT NULL REFERENCES products (product_id),
            seller_id           TEXT NOT NULL REFERENCES sellers (seller_id),
            shipping_limit_date TIMESTAMP,
            price               NUMERIC(10, 2) NOT NULL,
            freight_value       NUMERIC(10, 2) NOT NULL,
            PRIMARY KEY (order_id, order_item_id)
        )
        """,
    ),
    (
        "order_payments",
        """
        CREATE TABLE order_payments (
            order_id             TEXT NOT NULL REFERENCES orders (order_id),
            payment_sequential   INTEGER NOT NULL,
            payment_type         TEXT NOT NULL,
            payment_installments INTEGER NOT NULL,
            payment_value        NUMERIC(10, 2) NOT NULL,
            PRIMARY KEY (order_id, payment_sequential)
        )
        """,
    ),
    (
        # review_id alone is not unique (814 repeats); (review_id, order_id) is.
        "order_reviews",
        """
        CREATE TABLE order_reviews (
            review_id               TEXT NOT NULL,
            order_id                TEXT NOT NULL REFERENCES orders (order_id),
            review_score            INTEGER NOT NULL,
            review_comment_title    TEXT,
            review_comment_message  TEXT,
            review_creation_date    TIMESTAMP,
            review_answer_timestamp TIMESTAMP,
            PRIMARY KEY (review_id, order_id)
        )
        """,
    ),
]

TABLE_TO_CSV = {table: csv_name for csv_name, table in TABLE_NAME_MAP.items()}


def get_engine():
    """Create a SQLAlchemy engine for Postgres, reading connection info from .env."""
    load_dotenv()
    # URL.create escapes special characters in the password; string-building would not.
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        database=os.environ["POSTGRES_DB"],
    )
    return create_engine(url)


def create_schema(engine) -> None:
    """Create the 9 tables with real FKs, in dependency order."""
    # One transaction: if any statement fails, nothing is left half-created.
    with engine.begin() as conn:
        for table_name, _ in reversed(SCHEMA_DDL):
            conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
        for _, ddl in SCHEMA_DDL:
            conn.execute(text(ddl))


def load_csv_to_table(engine, csv_path: str, table_name: str) -> None:
    """Read a CSV, convert date columns, and append rows into an existing table."""
    df = pd.read_csv(csv_path)

    for col in DATE_COLUMN_BY_TABLE.get(table_name, []):
        df[col] = pd.to_datetime(df[col])

    for col in NULLABLE_INT_COLUMNS_BY_TABLE.get(table_name, []):
        df[col] = df[col].astype("Int64")

    # "append" keeps the tables created by create_schema; "replace" would drop them
    # and recreate them without keys.
    df.to_sql(table_name, engine, if_exists="append", index=False, chunksize=CHUNK_SIZE)


def verify_row_counts(engine) -> None:
    """Compare len(df) per CSV against SELECT COUNT(*) in Postgres."""
    mismatches = []
    with engine.connect() as conn:
        for table_name, _ in SCHEMA_DDL:
            csv_path = RAW_DATA_DIR / TABLE_TO_CSV[table_name]
            # len(df), not `wc -l`: quoted fields can contain newlines.
            expected = len(pd.read_csv(csv_path))
            actual = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one()
            status = "OK" if expected == actual else "MISMATCH"
            print(f"  {table_name:<36} csv={expected:>9,}  db={actual:>9,}  {status}")
            if expected != actual:
                mismatches.append(table_name)

    if mismatches:
        raise RuntimeError(f"Row count mismatch for: {', '.join(mismatches)}")


def main() -> None:
    """create_schema -> load_csv_to_table for all 9 tables -> verify_row_counts."""
    engine = get_engine()

    print("Creating schema...")
    create_schema(engine)

    for table_name, _ in SCHEMA_DDL:
        csv_path = RAW_DATA_DIR / TABLE_TO_CSV[table_name]
        print(f"Loading {table_name} from {csv_path.name}...")
        load_csv_to_table(engine, csv_path, table_name)

    print("Verifying row counts...")
    verify_row_counts(engine)


if __name__ == "__main__":
    main()
