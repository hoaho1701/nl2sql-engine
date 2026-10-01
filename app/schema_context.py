"""Generate schema DDL, business descriptions, and data-trap warnings for the RAG vector store."""

from sqlalchemy import inspect


def _column_ddl(column, dialect) -> str:
    """Render one column as 'name TYPE [NOT NULL]'."""
    parts = [column["name"], column["type"].compile(dialect=dialect)]
    if not column["nullable"]:
        parts.append("NOT NULL")
    return " ".join(parts)


def _pk_ddl(pk) -> str | None:
    """Render 'PRIMARY KEY (a, b)', or None if the table has no primary key."""
    columns = pk["constrained_columns"]
    if not columns:
        return None
    return f"PRIMARY KEY ({', '.join(columns)})"


def _fk_ddl(fk) -> str:
    """Render one 'FOREIGN KEY (...) REFERENCES table (...)' clause."""
    local = ", ".join(fk["constrained_columns"])
    remote = ", ".join(fk["referred_columns"])
    return f"FOREIGN KEY ({local}) REFERENCES {fk['referred_table']} ({remote})"


def _table_ddl(insp, table, dialect) -> str:
    """Render the full CREATE TABLE statement for one table."""
    parts = [_column_ddl(column, dialect) for column in insp.get_columns(table)]
    pk = _pk_ddl(insp.get_pk_constraint(table))
    if pk:
        parts.append(pk)
    parts += [_fk_ddl(fk) for fk in insp.get_foreign_keys(table)]
    return f"CREATE TABLE {table} (\n    " + ",\n    ".join(parts) + "\n)"


def generate_ddl(engine) -> list[str]:
    """Use sqlalchemy.inspect(engine) to generate CREATE TABLE statements, including real FKs."""
    insp = inspect(engine)
    # Parents first; the sorted list ends with a (None, [...]) entry that is not a table.
    table_names = [name for name, _ in insp.get_sorted_table_and_fkc_names() if name]
    return [_table_ddl(insp, name, engine.dialect) for name in table_names]


TABLE_DESCRIPTIONS = {
    "customers": (
        "One row per customer_id, which is scoped to a single order (a repeat "
        "buyer gets a new customer_id for each order). customer_unique_id is the "
        "stable identifier for the actual person across multiple orders — use it, "
        "not customer_id, when counting distinct customers. customer_zip_code_prefix "
        "joins to geolocation.geolocation_zip_code_prefix without a declared foreign "
        "key, and that join fans out rows (see the geolocation fan-out warning)."
    ),
    "geolocation": (
        "Brazilian zip-code-prefix-level coordinates (lat/lng) and city/state. "
        "geolocation_zip_code_prefix is NOT unique: 1,000,163 rows but only 19,015 "
        "distinct prefixes. Joining on this column without deduplication fans out "
        "any COUNT/SUM computed above the join."
    ),
    "order_items": (
        "One row per item within an order. order_item_id is the item's sequence "
        "number inside that order, NOT a quantity — never SUM(order_item_id) to "
        "count items, use COUNT(*) instead. price and freight_value are per item. "
        "seller_id joins to sellers, product_id joins to products, order_id joins "
        "to orders."
    ),
    "order_payments": (
        "Payment records for an order. A single order can have multiple payment "
        "rows (e.g. split/installment payments), so joining order_payments to "
        "order-level tables can multiply rows — deduplicate by order_id before "
        "aggregating per order. payment_type is one of: boleto, credit_card, "
        "debit_card, voucher, not_defined. payment_installments is the number of "
        "installments, not a monetary amount."
    ),
    "order_reviews": (
        "Customer reviews for an order. review_score is an integer 1-5 (1=worst, "
        "5=best). review_comment_title and review_comment_message are optional "
        "free text and are NULL most of the time (~88% and ~59% NULL respectively) "
        "— a missing comment is normal, not a data error."
    ),
    "orders": (
        "One row per order. order_status is one of: approved, canceled, created, "
        "delivered, invoiced, processing, shipped, unavailable. "
        "order_purchase_timestamp is always populated. order_approved_at, "
        "order_delivered_carrier_date, and order_delivered_customer_date can be "
        "NULL, meaning that stage of the order hasn't happened yet — e.g. "
        "order_delivered_customer_date is NULL for almost every non-'delivered' "
        "order. A small number of 'delivered'/'created'/'approved' orders also "
        "have NULL timestamps here, which is data-quality noise rather than a "
        "meaningful business state."
    ),
    "products": (
        "Product catalog. product_category_name can be NULL (~1.9% of rows), which "
        "an INNER JOIN to the translation table silently drops. "
        "product_name_lenght and product_description_lenght "
        "are spelled this way in the source data itself, not a typo to fix. Join "
        "to product_category_name_translation via product_category_name to get "
        "the English category name."
    ),
    "sellers": (
        "One row per seller_id. seller_zip_code_prefix joins to "
        "geolocation.geolocation_zip_code_prefix (same fan-out caveat as customers)."
    ),
    "product_category_name_translation": (
        "Lookup table mapping the Portuguese product_category_name used in "
        "products to its English translation, product_category_name_english."
    ),
}

NON_UNIQUE_PARENT_KEYS = {
    "geolocation.geolocation_zip_code_prefix": (
        "1,000,163 rows but only 19,015 distinct zip prefixes (about 53 rows per "
        "prefix). Joining customers or sellers to geolocation on this column "
        "without deduplication fans out any COUNT/SUM computed above the join: "
        "measured, customers JOIN geolocation returns 15,083,455 rows for 99,441 "
        "customers (~152x) and sellers JOIN geolocation returns 435,087 rows for "
        "3,095 sellers (~140x). To attach coordinates, first collapse geolocation "
        "to one row per prefix (GROUP BY geolocation_zip_code_prefix with AVG of "
        "lat/lng) and join to that, or use COUNT(DISTINCT ...)."
    ),
}

# Real one-to-many joins (these have proper foreign keys, but still multiply rows).
ONE_TO_MANY_JOINS = {
    "orders -> order_items": (
        "An order has one or more items: 9,803 orders have more than one row in "
        "order_items. Joining orders to order_items repeats every order-level "
        "column once per item, so count orders with COUNT(DISTINCT order_id) and "
        "do not SUM order-level values after this join."
    ),
    "orders -> order_payments": (
        "An order can have several payment rows (split or installment payments): "
        "2,961 of the 99,440 orders that have payments have more than one. "
        "Joining orders (or order_items) to order_payments repeats rows and "
        "inflates SUM/COUNT; aggregate payments per order_id first, or use "
        "COUNT(DISTINCT order_id)."
    ),
    "orders -> order_reviews": (
        "An order can have more than one review: 547 orders have several rows in "
        "order_reviews. Aggregate reviews per order_id (or deduplicate) before "
        "joining them to order-level or item-level data."
    ),
}

# Relationships that exist in the data but are NOT declared as foreign keys, so they
# do not appear in the generated DDL and must be described explicitly.
JOINS_WITHOUT_FK = {
    "customers.customer_zip_code_prefix -> geolocation.geolocation_zip_code_prefix": (
        "No foreign key is declared because geolocation_zip_code_prefix is not "
        "unique. It is a many-to-many style join that fans out; deduplicate "
        "geolocation to one row per prefix before joining."
    ),
    "sellers.seller_zip_code_prefix -> geolocation.geolocation_zip_code_prefix": (
        "No foreign key is declared because geolocation_zip_code_prefix is not "
        "unique. Deduplicate geolocation to one row per prefix before joining."
    ),
    "products.product_category_name -> product_category_name_translation.product_category_name": (
        "No foreign key is declared because some categories used in products are "
        "missing from the translation table: pc_gamer (3 products) and "
        "portateis_cozinha_e_preparadores_de_alimentos (10 products). The "
        "translation table itself is unique per category, so the join does not "
        "fan out; use LEFT JOIN to keep products without a translation."
    ),
}

NULLABLE_CHILD_KEYS = {
    "products.product_category_name": (
        "~1.9% NULL (610 of 32,951 products). An INNER JOIN from products to "
        "product_category_name_translation will silently drop these rows; "
        "use LEFT JOIN if uncategorized products should be kept in the result."
    ),
}

# Rows that an INNER JOIN silently drops because the other side has no match.
INNER_JOIN_ROW_LOSS = {
    "customers.customer_zip_code_prefix": (
        "278 customers (157 distinct zip prefixes) have a prefix that does not "
        "exist in geolocation, so an INNER JOIN to geolocation drops them: even "
        "with geolocation deduplicated, only 99,163 of 99,441 customers match."
    ),
    "sellers.seller_zip_code_prefix": (
        "7 sellers have a zip prefix that does not exist in geolocation and are "
        "dropped by an INNER JOIN to geolocation."
    ),
    "products.product_category_name": (
        "13 products with a non-NULL category (pc_gamer and "
        "portateis_cozinha_e_preparadores_de_alimentos) have no row in "
        "product_category_name_translation and are dropped by an INNER JOIN."
    ),
    "orders.order_id": (
        "Not every order has child rows: 775 orders have no order_items, 1 has no "
        "order_payments, and 768 have no order_reviews. An INNER JOIN from orders "
        "to any of these tables drops those orders; use LEFT JOIN to keep them."
    ),
}

# Join paths between tables that are not directly related.
JOIN_PATHS = {
    "customer to product": (
        "customers.customer_id = orders.customer_id, then orders.order_id = "
        "order_items.order_id, then order_items.product_id = products.product_id."
    ),
    "order to seller": (
        "orders.order_id = order_items.order_id, then order_items.seller_id = "
        "sellers.seller_id. Sellers are linked to orders only through order_items."
    ),
    "product English category name": (
        "products.product_category_name = "
        "product_category_name_translation.product_category_name (use LEFT JOIN)."
    ),
    "order payments and reviews": (
        "order_payments and order_reviews both hang off orders through order_id; "
        "they are not directly related to order_items, customers, or sellers."
    ),
}


def build_documentation_chunks() -> list[str]:
    """Flatten the documentation dicts into independent text chunks, each embedded
    separately in the vector store."""
    chunks = [
        f"Table {table}: {description}"
        for table, description in TABLE_DESCRIPTIONS.items()
    ]
    chunks += [
        f"Fan-out risk on {column}: {warning}"
        for column, warning in NON_UNIQUE_PARENT_KEYS.items()
    ]
    chunks += [
        f"One-to-many join {join}: {warning}"
        for join, warning in ONE_TO_MANY_JOINS.items()
    ]
    chunks += [
        f"Join without a foreign key, {join}: {note}"
        for join, note in JOINS_WITHOUT_FK.items()
    ]
    chunks += [
        f"Nullable foreign key {column}: {warning}"
        for column, warning in NULLABLE_CHILD_KEYS.items()
    ]
    chunks += [
        f"Rows lost by INNER JOIN on {column}: {warning}"
        for column, warning in INNER_JOIN_ROW_LOSS.items()
    ]
    chunks += [
        f"Join path, {name}: {path}"
        for name, path in JOIN_PATHS.items()
    ]
    return chunks
