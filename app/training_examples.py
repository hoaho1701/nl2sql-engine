"""Training examples: (question, sql) pairs stored in the vector store as few-shot context.

These must stay disjoint from eval_test_set.py: a question or query that appears in both
would let the model see the answer to an eval case, which makes the accuracy meaningless.
Every query here has been run against the real database.
"""

TRAINING_EXAMPLES = [
    # -- simple filtered count --
    {
        "question": "How many orders were canceled?",
        "sql": "SELECT COUNT(*) FROM orders WHERE order_status = 'canceled';",
    },
    # -- multi-table join, GROUP BY, top-N, English category names --
    {
        "question": "What are the 5 product categories with the most items sold, by English name?",
        "sql": (
            "SELECT t.product_category_name_english, COUNT(*) AS items_sold "
            "FROM order_items oi "
            "JOIN products p ON p.product_id = oi.product_id "
            "JOIN product_category_name_translation t "
            "ON t.product_category_name = p.product_category_name "
            "GROUP BY t.product_category_name_english "
            "ORDER BY items_sold DESC LIMIT 5;"
        ),
    },
    # -- parents without children: LEFT JOIN anti-join instead of INNER JOIN --
    {
        "question": "How many orders have no review at all?",
        "sql": (
            "SELECT COUNT(*) FROM orders o "
            "LEFT JOIN order_reviews r ON r.order_id = o.order_id "
            "WHERE r.order_id IS NULL;"
        ),
    },
    {
        "question": "How many distinct products have been sold?",
        "sql": (
            "SELECT COUNT(DISTINCT product_id) FROM order_items;"
        )
    },
    {
        "question": "How many products have no weight recorded?",
        "sql": (
            "SELECT COUNT(*) FROM products WHERE product_weight_g IS NULL;"
        )
    },
    # -- HAVING on a grouped subquery --
    {
        "question": "How many sellers have sold more than 100 items?",
        "sql": (
            "SELECT COUNT(*) AS total_sellers_over_100 "
            "FROM ("
            "SELECT seller_id "
            "FROM order_items "
            "GROUP BY seller_id "
            "HAVING COUNT(order_item_id) > 100"
            ") AS qualified_sellers;"
        ),
    },
    # -- date range filter (half-open interval) --
    {
        "question": "How many orders were purchased in 2017?",
        "sql": (
            "SELECT COUNT(*) FROM orders "
            "WHERE order_purchase_timestamp >= '2017-01-01' "
            "AND order_purchase_timestamp < '2018-01-01';"
        ),
    },
    # -- GROUP BY a truncated date --
    {
        "question": "How many orders were purchased in each month of 2017?",
        "sql": (
            "SELECT DATE_TRUNC('month', order_purchase_timestamp) AS purchase_month, "
            "COUNT(*) AS total_orders "
            "FROM orders "
            "WHERE order_purchase_timestamp >= '2017-01-01' "
            "AND order_purchase_timestamp < '2018-01-01' "
            "GROUP BY purchase_month ORDER BY purchase_month;"
        ),
    },
    # -- difference between two timestamps, NULLs ignored by AVG --
    {
        "question": (
            "What is the average number of days between purchase and delivery "
            "for delivered orders?"
        ),
        "sql": (
            "SELECT ROUND(AVG(EXTRACT(EPOCH FROM "
            "(order_delivered_customer_date - order_purchase_timestamp)) / 86400)::numeric, 2) "
            "AS avg_delivery_days "
            "FROM orders WHERE order_status = 'delivered';"
        ),
    },
    # -- percentage: multiply by 100.0 to avoid integer division --
    {
        "question": "What percentage of orders were canceled?",
        "sql": (
            "SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE order_status = 'canceled') "
            "/ COUNT(*), 2) AS canceled_percentage "
            "FROM orders;"
        ),
    },
    # -- people, not rows: count customer_unique_id, since customer_id changes per order --
    {
        "question": "Which state has the most distinct customers?",
        "sql": (
            "SELECT customer_state, COUNT(DISTINCT customer_unique_id) AS total_customers "
            "FROM customers "
            "GROUP BY customer_state "
            "ORDER BY total_customers DESC LIMIT 1;"
        ),
    },
    # -- ORDER BY ... DESC LIMIT --
    {
        "question": "What are the 3 most expensive items ever sold, with their prices?",
        "sql": (
            "SELECT product_id, price "
            "FROM order_items "
            "ORDER BY price DESC LIMIT 3;"
        ),
    },
    # -- SUM per group on a single table --
    {
        "question": "What is the total payment value for each payment type?",
        "sql": (
            "SELECT payment_type, ROUND(SUM(payment_value), 2) AS total_value "
            "FROM order_payments "
            "GROUP BY payment_type ORDER BY total_value DESC;"
        ),
    },
    # -- an order can have several payment rows: group by order_id before filtering --
    {
        "question": "How many orders were paid with more than one payment?",
        "sql": (
            "SELECT COUNT(*) FROM ("
            "SELECT order_id FROM order_payments "
            "GROUP BY order_id HAVING COUNT(*) > 1"
            ") AS split_payments;"
        ),
    },
    # -- join two tables, aggregate the item-level column (no payments join: it would fan out) --
    {
        "question": "What is the total freight value for each seller state?",
        "sql": (
            "SELECT s.seller_state, ROUND(SUM(oi.freight_value), 2) AS total_freight "
            "FROM order_items oi "
            "JOIN sellers s ON s.seller_id = oi.seller_id "
            "GROUP BY s.seller_state ORDER BY total_freight DESC;"
        ),
    },
]
