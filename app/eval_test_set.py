"""Evaluation set: (question, gold_sql) pairs. Never add these to the vector store."""

EVAL_CASES = [
    # -- simple counts --
    {
        "question": "How many orders are there in total?",
        "gold_sql": "SELECT COUNT(*) FROM orders;",
    },
    {
        "question": "How many orders have been delivered?",
        "gold_sql": "SELECT COUNT(*) FROM orders WHERE order_status = 'delivered';",
    },
    # -- JOIN + AVG (dedupe order_payments by order_id to avoid fan-out from
    # installment payments before joining to review scores) --
    {
        "question": "What is the average review score for orders paid by credit card?",
        "gold_sql": (
            "SELECT AVG(r.review_score) "
            "FROM order_reviews r "
            "WHERE r.order_id IN ("
            "SELECT DISTINCT order_id FROM order_payments WHERE payment_type = 'credit_card'"
            ");"
        ),
    },
    # -- GROUP BY + top-1 --
    {
        "question": "Which product category appears in the most distinct orders?",
        "gold_sql": (
            "SELECT p.product_category_name, COUNT(DISTINCT oi.order_id) AS order_count "
            "FROM order_items oi "
            "JOIN products p ON oi.product_id = p.product_id "
            "GROUP BY p.product_category_name "
            "ORDER BY order_count DESC "
            "LIMIT 1;"
        ),
    },
    # -- NULL traps --
    {
        "question": "How many products have no category assigned?",
        "gold_sql": "SELECT COUNT(*) FROM products WHERE product_category_name IS NULL;",
    },
    {
        "question": "How many orders have not yet been delivered to the customer?",
        "gold_sql": "SELECT COUNT(*) FROM orders WHERE order_delivered_customer_date IS NULL;",
    },
    {
        "question": "How many reviews have no comment message written?",
        "gold_sql": "SELECT COUNT(*) FROM order_reviews WHERE review_comment_message IS NULL;",
    },
    # -- fan-out traps --
    {
        "question": "How many distinct zip code prefixes appear in the geolocation table?",
        "gold_sql": "SELECT COUNT(DISTINCT geolocation_zip_code_prefix) FROM geolocation;",
    },
    {
        "question": (
            "What is the average latitude and longitude of sellers, using their zip "
            "code prefix to look up geolocation coordinates?"
        ),
        "gold_sql": (
            "SELECT AVG(g.avg_lat), AVG(g.avg_lng) "
            "FROM sellers s "
            "JOIN ("
            "SELECT geolocation_zip_code_prefix, "
            "AVG(geolocation_lat) AS avg_lat, AVG(geolocation_lng) AS avg_lng "
            "FROM geolocation "
            "GROUP BY geolocation_zip_code_prefix"
            ") g ON s.seller_zip_code_prefix = g.geolocation_zip_code_prefix;"
        ),
    },
    # -- HAVING via subquery (customer_unique_id, not customer_id, since
    # customer_id is scoped to a single order) --
    {
        "question": "Which customers (by unique id) have placed more than one order?",
        "gold_sql": (
            "SELECT c.customer_unique_id, COUNT(DISTINCT o.order_id) AS order_count "
            "FROM customers c "
            "JOIN orders o ON c.customer_id = o.customer_id "
            "GROUP BY c.customer_unique_id "
            "HAVING COUNT(DISTINCT o.order_id) > 1;"
        ),
    },
    # -- multi-column sum --
    {
        "question": "What is the total price and total freight value across all order items?",
        "gold_sql": "SELECT SUM(price), SUM(freight_value) FROM order_items;",
    },
    # -- date filter --
    {
        "question": "How many orders were purchased in January 2018?",
        "gold_sql": (
            "SELECT COUNT(*) FROM orders "
            "WHERE order_purchase_timestamp >= '2018-01-01' "
            "AND order_purchase_timestamp < '2018-02-01';"
        ),
    },
    # -- GROUP BY max --
    {
        "question": "Which seller has the highest total sales (sum of item price)?",
        "gold_sql": (
            "SELECT seller_id, SUM(price) AS total_sales "
            "FROM order_items "
            "GROUP BY seller_id "
            "ORDER BY total_sales DESC "
            "LIMIT 1;"
        ),
    },
    # -- date comparison --
    {
        "question": "How many orders were delivered later than their estimated delivery date?",
        "gold_sql": (
            "SELECT COUNT(*) FROM orders "
            "WHERE order_delivered_customer_date > order_estimated_delivery_date;"
        ),
    },
    # -- 3+ table join --
    {
        "question": (
            "What is the total revenue (sum of item price) per product category for "
            "customers located in the state of SP?"
        ),
        "gold_sql": (
            "SELECT p.product_category_name, SUM(oi.price) AS total_revenue "
            "FROM order_items oi "
            "JOIN orders o ON oi.order_id = o.order_id "
            "JOIN customers c ON o.customer_id = c.customer_id "
            "JOIN products p ON oi.product_id = p.product_id "
            "WHERE c.customer_state = 'SP' "
            "GROUP BY p.product_category_name "
            "ORDER BY total_revenue DESC;"
        ),
    },
    # -- multi-row results --
    {
        "question": "List all distinct payment types used.",
        "gold_sql": "SELECT DISTINCT payment_type FROM order_payments ORDER BY payment_type;",
    },
    {
        "question": "How many orders are there for each order status?",
        "gold_sql": (
            "SELECT order_status, COUNT(*) FROM orders "
            "GROUP BY order_status ORDER BY order_status;"
        ),
    },
    {
        "question": "How many sellers are located in each state?",
        "gold_sql": (
            "SELECT seller_state, COUNT(*) FROM sellers "
            "GROUP BY seller_state ORDER BY seller_state;"
        ),
    },
]
