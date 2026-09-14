"""Generate schema DDL, business descriptions, and data-trap warnings for the RAG vector store."""


def generate_ddl(engine) -> list[str]:
    """Use sqlalchemy.inspect(engine) to generate CREATE TABLE statements, including real FKs."""
    raise NotImplementedError


TABLE_DESCRIPTIONS = {
    "customers": (
        "One row per customer_id, which is scoped to a single order (a repeat "
        "buyer gets a new customer_id for each order). customer_unique_id is the "
        "stable identifier for the actual person across multiple orders — use it, "
        "not customer_id, when counting distinct customers. customer_zip_code_prefix "
        "joins to geolocation.geolocation_zip_code_prefix (see NON_UNIQUE_PARENT_KEYS "
        "for a fan-out caveat on that join)."
    ),
    "geolocation": (
        "Brazilian zip-code-prefix-level coordinates (lat/lng) and city/state. "
        "geolocation_zip_code_prefix is NOT unique: 1,000,163 rows but only 19,015 "
        "distinct prefixes. Joining on this column without deduplication fans out "
        "any COUNT/SUM computed above the join — see NON_UNIQUE_PARENT_KEYS."
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
        "Product catalog. product_category_name can be NULL (~1.9% of rows) — see "
        "NULLABLE_CHILD_KEYS. product_name_lenght and product_description_lenght "
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
        "1,000,163 rows but only 19,015 distinct zip prefixes. Joining "
        "customers or sellers to geolocation on this column without "
        "DISTINCT/deduplication will fan out any COUNT/SUM computed above "
        "the join."
    ),
}

NULLABLE_CHILD_KEYS = {
    "products.product_category_name": (
        "~1.9% NULL. An INNER JOIN from products to "
        "product_category_name_translation will silently drop these rows; "
        "use LEFT JOIN if uncategorized products should be kept in the result."
    ),
}


def build_documentation_chunks() -> list[str]:
    """Flatten TABLE_DESCRIPTIONS / NON_UNIQUE_PARENT_KEYS / NULLABLE_CHILD_KEYS into
    independent text chunks, each embedded separately in the vector store."""
    chunks = [
        f"Table {table}: {description}"
        for table, description in TABLE_DESCRIPTIONS.items()
    ]
    chunks += [
        f"Fan-out risk on {column}: {warning}"
        for column, warning in NON_UNIQUE_PARENT_KEYS.items()
    ]
    chunks += [
        f"Nullable foreign key {column}: {warning}"
        for column, warning in NULLABLE_CHILD_KEYS.items()
    ]
    return chunks
