"""Load the 9 Olist CSVs into Postgres with real foreign keys."""

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


def get_engine():
    """Create a SQLAlchemy engine for Postgres, reading connection info from .env."""
    raise NotImplementedError


def create_schema(engine) -> None:
    """Create the 9 tables with real FKs, in dependency order."""
    raise NotImplementedError


def load_csv_to_table(engine, csv_path: str, table_name: str) -> None:
    """Read a CSV, convert date columns, and append rows into an existing table."""
    raise NotImplementedError


def verify_row_counts(engine) -> None:
    """Compare len(df) per CSV against SELECT COUNT(*) in Postgres."""
    raise NotImplementedError


def main() -> None:
    """create_schema -> load_csv_to_table for all 9 tables -> verify_row_counts."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
