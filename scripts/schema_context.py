from sqlalchemy import create_engine, inspect

DB_PATH = "data/olist.db"

# Short description of what one row in each table represents.
# Kept separate from the DB schema itself because the LLM only ever
# sees this generated text context, not the actual database.
TABLE_DESCRIPTIONS = {
    "orders": (
        "Each line represents an order. order_status is one of: "
        "approved, canceled, created, delivered, invoiced, processing, shipped, unavailable. "
        "order_approved_at, order_delivered_carrier_date, and order_delivered_customer_date "
        "are NULL when the order simply hasn't reached that stage yet — not a data quality issue."
    ),
    "products": (
        "Each line represents a product. product_category_name can be NULL "
        "(~610 products have no category). Note: product_name_lenght and "
        "product_description_lenght are spelled this way in the source data, not a typo."
    ),
    "sellers": "Each line represents a seller. seller_state is a 2-letter Brazilian state code (e.g. SP, RJ).",
    "customers": "Each line represents a customer. customer_state is a 2-letter Brazilian state code (e.g. SP, RJ).",
    "geolocation": "Each line represents one lat/lng sample for a zip code prefix. geolocation_state is a 2-letter Brazilian state code (e.g. SP, RJ).",
    "order_items": (
        "Each line represents one item within an order — an order can contain multiple items. "
        "order_item_id is the 1-based position of the item within its order (1, 2, 3, ...), NOT a "
        "quantity or amount — to count how many items were sold, use COUNT(order_item_id) or COUNT(*), "
        "never SUM(order_item_id)."
    ),
    "order_payments": (
        "Each line represents one payment entry for an order — an order can have "
        "multiple payment entries (e.g. installments). payment_type is one of: "
        "boleto, credit_card, debit_card, not_defined, voucher."
    ),
    "order_reviews": (
        "Each line represents a review of an order. review_score ranges from 1 (worst) to 5 (best). "
        "review_comment_title and review_comment_message are frequently NULL — many customers "
        "leave a score without writing a comment."
    ),
    "product_category_name_translation": "Lookup table mapping Portuguese product category names to their English translation."
}

# Relationships between tables — these replace real FK constraints, which
# the database doesn't have (SQLite makes adding FKs after table creation hard).
# Format: (child_table, child_col, parent_table, parent_col)
RELATIONSHIPS = [
    ("orders", "customer_id", "customers", "customer_id"),
    ("order_reviews", "order_id", "orders", "order_id"),
    ("order_payments", "order_id", "orders", "order_id"),
    ("order_items", "order_id", "orders", "order_id"),
    ("order_items", "product_id", "products", "product_id"),
    ("order_items", "seller_id", "sellers", "seller_id"),
    ("sellers", "seller_zip_code_prefix", "geolocation", "geolocation_zip_code_prefix"),
    ("customers", "customer_zip_code_prefix", "geolocation", "geolocation_zip_code_prefix"),
    ("products", "product_category_name", "product_category_name_translation", "product_category_name"),
]

# Parent (table, column) pairs that are NOT unique — geolocation has ~52 rows
# per zip prefix on average, so joining on it fans out rows unless the
# caller deduplicates first. Flagged separately so the LLM is warned in the
# generated context instead of silently producing wrong aggregate results.
NON_UNIQUE_PARENT_KEYS = {
    ("geolocation", "geolocation_zip_code_prefix"),
}

# Child (table, column) pairs that can be NULL — an INNER JOIN on these silently
# drops rows with no value, which is usually not what's wanted.
NULLABLE_CHILD_KEYS = {
    ("products", "product_category_name"): "~610 products have no category",
}


def build_schema_context(engine) -> str:
    # inspect() works the same way regardless of dialect (SQLite, Postgres, ...),
    # so this function doesn't need to change when the DB backend changes later.
    inspector = inspect(engine)
    lines = []

    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)

        comment = TABLE_DESCRIPTIONS.get(table_name, "")
        column_lines = [f" {col['name']} {col['type']}" for col in columns]

        # Join column lines with ",\n" instead of appending "," per line
        # so the last column doesn't end up with a trailing comma.
        table_block = (
            f"-- {comment}\n"
            f"CREATE TABLE {table_name} (\n"
            + ",\n".join(column_lines)
            + "\n);"
        )
        lines.append(table_block)

    lines.append("-- Relationships:")
    for child_table, child_col, parent_table, parent_col in RELATIONSHIPS:
        line = f"-- {child_table}.{child_col} -> {parent_table}.{parent_col}"
        if (parent_table, parent_col) in NON_UNIQUE_PARENT_KEYS:
            line += " (NOTE: not unique — one value maps to many rows, deduplicate before joining)"
        nullable_reason = NULLABLE_CHILD_KEYS.get((child_table, child_col))
        if nullable_reason:
            line += f" (NOTE: nullable — {nullable_reason}, use LEFT JOIN to keep them)"
        lines.append(line)

    return "\n".join(lines)


if __name__ == "__main__":
    engine = create_engine(f"sqlite:///{DB_PATH}")
    context = build_schema_context(engine)
    print(context)
