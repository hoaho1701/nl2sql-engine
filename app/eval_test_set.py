"""Evaluation set: (question, gold_sql) pairs. Never add these to the vector store.

Version 3 = the 18 "core" cases of version 2 (case 14 reworded, its gold unchanged) plus 22 new cases.
Every case has an id, a subset and a kind:
  subset "core"    the version-2 cases, kept so results stay comparable with older log rows
  subset "dev"     new cases that may be looked at while building and tuning a feature
  subset "heldout" new cases that must NOT be run or inspected while building a feature; they are
                   run once at the end (the commit that added them is recorded in the project log)
  kind: fanout (a tempting join multiplies rows), control (a join that looks risky but is safe),
        null, definition (a business definition stated in the question), ranking, other
app/verify_eval_set.py re-checks the new gold queries against the CSV files with pandas.
"""

EVAL_VERSION = 3

EVAL_CASES = [
    # -- simple counts --
    {
        "id": "Q01",
        "subset": "core",
        "kind": "other",
        "question": "How many orders are there in total?",
        "gold_sql": "SELECT COUNT(*) FROM orders;",
    },
    {
        "id": "Q02",
        "subset": "core",
        "kind": "other",
        "question": "How many orders have been delivered?",
        "gold_sql": "SELECT COUNT(*) FROM orders WHERE order_status = 'delivered';",
    },
    # -- JOIN + AVG (dedupe order_payments by order_id to avoid fan-out from
    # installment payments before joining to review scores) --
    {
        "id": "Q03",
        "subset": "core",
        "kind": "fanout",
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
        "id": "Q04",
        "subset": "core",
        "kind": "ranking",
        "question": (
            "Which product category appears in the most distinct orders? "
            "Use the English category name."
        ),
        "gold_sql": (
            "SELECT t.product_category_name_english, COUNT(DISTINCT oi.order_id) AS order_count "
            "FROM order_items oi "
            "JOIN products p ON oi.product_id = p.product_id "
            "JOIN product_category_name_translation t "
            "ON p.product_category_name = t.product_category_name "
            "GROUP BY t.product_category_name_english "
            "ORDER BY order_count DESC "
            "LIMIT 1;"
        ),
    },
    # -- NULL traps --
    {
        "id": "Q05",
        "subset": "core",
        "kind": "null",
        "question": "How many products have no category assigned?",
        "gold_sql": "SELECT COUNT(*) FROM products WHERE product_category_name IS NULL;",
    },
    {
        "id": "Q06",
        "subset": "core",
        "kind": "null",
        "question": "How many orders have not yet been delivered to the customer?",
        "gold_sql": "SELECT COUNT(*) FROM orders WHERE order_delivered_customer_date IS NULL;",
    },
    {
        "id": "Q07",
        "subset": "core",
        "kind": "null",
        "question": "How many reviews have no comment message written?",
        "gold_sql": "SELECT COUNT(*) FROM order_reviews WHERE review_comment_message IS NULL;",
    },
    # -- fan-out traps --
    {
        "id": "Q08",
        "subset": "core",
        "kind": "fanout",
        "question": "How many distinct zip code prefixes appear in the geolocation table?",
        "gold_sql": "SELECT COUNT(DISTINCT geolocation_zip_code_prefix) FROM geolocation;",
    },
    {
        "id": "Q09",
        "subset": "core",
        "kind": "fanout",
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
        "id": "Q10",
        "subset": "core",
        "kind": "other",
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
        "id": "Q11",
        "subset": "core",
        "kind": "other",
        "question": "What is the total price and total freight value across all order items?",
        "gold_sql": "SELECT SUM(price), SUM(freight_value) FROM order_items;",
    },
    # -- date filter --
    {
        "id": "Q12",
        "subset": "core",
        "kind": "other",
        "question": "How many orders were purchased in January 2018?",
        "gold_sql": (
            "SELECT COUNT(*) FROM orders "
            "WHERE order_purchase_timestamp >= '2018-01-01' "
            "AND order_purchase_timestamp < '2018-02-01';"
        ),
    },
    # -- GROUP BY max --
    {
        "id": "Q13",
        "subset": "core",
        "kind": "ranking",
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
        "id": "Q14",
        "subset": "core",
        "kind": "other",
        "question": (
            "How many orders have a delivery date recorded that is later than the estimated "
            "delivery date, regardless of order status?"
        ),
        "gold_sql": (
            "SELECT COUNT(*) FROM orders "
            "WHERE order_delivered_customer_date > order_estimated_delivery_date;"
        ),
    },
    # -- 3+ table join --
    {
        "id": "Q15",
        "subset": "core",
        "kind": "other",
        "question": (
            "What is the total revenue (sum of item price) per product category for "
            "customers located in the state of SP? Use the English category name."
        ),
        "gold_sql": (
            "SELECT t.product_category_name_english, SUM(oi.price) AS total_revenue "
            "FROM order_items oi "
            "JOIN orders o ON oi.order_id = o.order_id "
            "JOIN customers c ON o.customer_id = c.customer_id "
            "JOIN products p ON oi.product_id = p.product_id "
            "JOIN product_category_name_translation t "
            "ON p.product_category_name = t.product_category_name "
            "WHERE c.customer_state = 'SP' "
            "GROUP BY t.product_category_name_english "
            "ORDER BY total_revenue DESC;"
        ),
    },
    # -- multi-row results --
    {
        "id": "Q16",
        "subset": "core",
        "kind": "other",
        "question": "List all distinct payment types used.",
        "gold_sql": "SELECT DISTINCT payment_type FROM order_payments ORDER BY payment_type;",
    },
    {
        "id": "Q17",
        "subset": "core",
        "kind": "other",
        "question": "How many orders are there for each order status?",
        "gold_sql": (
            "SELECT order_status, COUNT(*) FROM orders "
            "GROUP BY order_status ORDER BY order_status;"
        ),
    },
    {
        "id": "Q18",
        "subset": "core",
        "kind": "other",
        "question": "How many sellers are located in each state?",
        "gold_sql": (
            "SELECT seller_state, COUNT(*) FROM sellers "
            "GROUP BY seller_state ORDER BY seller_state;"
        ),
    },
    # -- version 3: 14 dev and 8 held-out cases (see the module docstring) --
    {
        "id": "F3",
        "subset": "dev",
        "kind": "fanout",
        "question": "What is the total freight value of orders that were paid by credit card?",
        "gold_sql": (
            "SELECT ROUND(SUM(freight_value)::numeric, 2) FROM order_items WHERE order_id IN "
            "(SELECT order_id FROM order_payments WHERE payment_type = 'credit_card');"
        ),
    },
    {
        "id": "F4",
        "subset": "dev",
        "kind": "fanout",
        "question": (
            "What is the average total payment value per order, for orders that have more than "
            "one item?"
        ),
        "gold_sql": (
            "SELECT ROUND(AVG(t.total)::numeric, 2) FROM (SELECT order_id, SUM(payment_value) AS "
            "total FROM order_payments WHERE order_id IN (SELECT order_id FROM order_items GROUP "
            "BY order_id HAVING COUNT(*) > 1) GROUP BY order_id) t;"
        ),
    },
    {
        "id": "F5",
        "subset": "dev",
        "kind": "fanout",
        "question": "What is the total price of items in orders that received a review score of 5?",
        "gold_sql": (
            "SELECT ROUND(SUM(price)::numeric, 2) FROM order_items WHERE order_id IN (SELECT "
            "order_id FROM order_reviews WHERE review_score = 5);"
        ),
    },
    {
        "id": "F6",
        "subset": "dev",
        "kind": "fanout",
        "question": "How many customers live in a zip code prefix that appears in the geolocation table?",
        "gold_sql": (
            "SELECT COUNT(*) FROM customers c WHERE EXISTS (SELECT 1 FROM geolocation g WHERE "
            "g.geolocation_zip_code_prefix = c.customer_zip_code_prefix);"
        ),
    },
    {
        "id": "F8",
        "subset": "dev",
        "kind": "fanout",
        "question": (
            "What is the average latitude and longitude of customers in the state of RJ, using "
            "their zip code prefix to look up geolocation coordinates?"
        ),
        "gold_sql": (
            "SELECT ROUND(AVG(g.lat)::numeric, 4), ROUND(AVG(g.lng)::numeric, 4) FROM customers c "
            "JOIN (SELECT geolocation_zip_code_prefix AS zip, AVG(geolocation_lat) AS lat, "
            "AVG(geolocation_lng) AS lng FROM geolocation GROUP BY geolocation_zip_code_prefix) g "
            "ON g.zip = c.customer_zip_code_prefix WHERE c.customer_state = 'RJ';"
        ),
    },
    {
        "id": "F9",
        "subset": "dev",
        "kind": "fanout",
        "question": "How many order items belong to orders that were paid with a voucher?",
        "gold_sql": (
            "SELECT COUNT(*) FROM order_items WHERE order_id IN (SELECT order_id FROM "
            "order_payments WHERE payment_type = 'voucher');"
        ),
    },
    {
        "id": "F11",
        "subset": "dev",
        "kind": "fanout",
        "question": (
            "What is the average price of items in orders that were paid in more than 5 "
            "installments?"
        ),
        "gold_sql": (
            "SELECT ROUND(AVG(price)::numeric, 2) FROM order_items WHERE order_id IN (SELECT "
            "order_id FROM order_payments WHERE payment_installments > 5);"
        ),
    },
    {
        "id": "C1",
        "subset": "dev",
        "kind": "control",
        "question": "What is the total payment value of orders placed by customers in the state of SP?",
        "gold_sql": (
            "SELECT ROUND(SUM(p.payment_value)::numeric, 2) FROM order_payments p JOIN orders o "
            "ON o.order_id = p.order_id JOIN customers c ON c.customer_id = o.customer_id WHERE "
            "c.customer_state = 'SP';"
        ),
    },
    {
        "id": "N3",
        "subset": "dev",
        "kind": "null",
        "question": "How many delivered orders have no delivery date recorded?",
        "gold_sql": (
            "SELECT COUNT(*) FROM orders WHERE order_status = 'delivered' AND "
            "order_delivered_customer_date IS NULL;"
        ),
    },
    {
        "id": "N4",
        "subset": "dev",
        "kind": "null",
        "question": "What is the average weight in grams of products that have no category assigned?",
        "gold_sql": (
            "SELECT ROUND(AVG(product_weight_g)::numeric, 2) FROM products WHERE "
            "product_category_name IS NULL;"
        ),
    },
    {
        "id": "N5",
        "subset": "dev",
        "kind": "null",
        "question": "How many orders have no approval timestamp recorded?",
        "gold_sql": "SELECT COUNT(*) FROM orders WHERE order_approved_at IS NULL;",
    },
    {
        "id": "D2",
        "subset": "dev",
        "kind": "definition",
        "question": (
            "How many distinct customers, by unique id, placed orders that were purchased in "
            "2017?"
        ),
        "gold_sql": (
            "SELECT COUNT(DISTINCT c.customer_unique_id) FROM orders o JOIN customers c ON "
            "c.customer_id = o.customer_id WHERE EXTRACT(YEAR FROM o.order_purchase_timestamp) = "
            "2017;"
        ),
    },
    {
        "id": "D3",
        "subset": "dev",
        "kind": "definition",
        "question": (
            "Among delivered orders that have a delivery date recorded, what percentage arrived "
            "later than the estimated delivery date? Round to 2 decimals."
        ),
        "gold_sql": (
            "SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE order_delivered_customer_date > "
            "order_estimated_delivery_date) / COUNT(*), 2) FROM orders WHERE order_status = "
            "'delivered' AND order_delivered_customer_date IS NOT NULL;"
        ),
    },
    {
        "id": "R3",
        "subset": "dev",
        "kind": "ranking",
        "question": "Which 5 sellers have the most distinct orders, and how many orders does each have?",
        "gold_sql": (
            "SELECT seller_id, COUNT(DISTINCT order_id) FROM order_items GROUP BY seller_id ORDER "
            "BY COUNT(DISTINCT order_id) DESC, seller_id LIMIT 5;"
        ),
    },
    {
        "id": "F1",
        "subset": "heldout",
        "kind": "fanout",
        "question": (
            "What is the total payment value of orders that contain at least one item from the "
            "product category health_beauty? Use the English category name."
        ),
        "gold_sql": (
            "SELECT ROUND(SUM(p.payment_value)::numeric, 2) FROM order_payments p WHERE "
            "p.order_id IN (SELECT oi.order_id FROM order_items oi JOIN products pr ON "
            "pr.product_id = oi.product_id JOIN product_category_name_translation t ON "
            "t.product_category_name = pr.product_category_name WHERE "
            "t.product_category_name_english = 'health_beauty');"
        ),
    },
    {
        "id": "F7",
        "subset": "heldout",
        "kind": "fanout",
        "question": "How many sellers have at least one geolocation entry for their zip code prefix?",
        "gold_sql": (
            "SELECT COUNT(*) FROM sellers s WHERE EXISTS (SELECT 1 FROM geolocation g WHERE "
            "g.geolocation_zip_code_prefix = s.seller_zip_code_prefix);"
        ),
    },
    {
        "id": "F10",
        "subset": "heldout",
        "kind": "fanout",
        "question": (
            "What is the total payment value of orders that contain at least one item from a "
            "seller located in the state of RJ?"
        ),
        "gold_sql": (
            "SELECT ROUND(SUM(payment_value)::numeric, 2) FROM order_payments WHERE order_id IN "
            "(SELECT i.order_id FROM order_items i JOIN sellers s ON s.seller_id = i.seller_id "
            "WHERE s.seller_state = 'RJ');"
        ),
    },
    {
        "id": "F12",
        "subset": "heldout",
        "kind": "fanout",
        "question": "How many reviews were written for orders that contain more than one item?",
        "gold_sql": (
            "SELECT COUNT(*) FROM order_reviews WHERE order_id IN (SELECT order_id FROM "
            "order_items GROUP BY order_id HAVING COUNT(*) > 1);"
        ),
    },
    {
        "id": "C2",
        "subset": "heldout",
        "kind": "control",
        "question": "How many distinct customers (by unique id) have placed an order paid with a voucher?",
        "gold_sql": (
            "SELECT COUNT(DISTINCT c.customer_unique_id) FROM customers c JOIN orders o ON "
            "o.customer_id = c.customer_id JOIN order_payments p ON p.order_id = o.order_id WHERE "
            "p.payment_type = 'voucher';"
        ),
    },
    {
        "id": "N1",
        "subset": "heldout",
        "kind": "null",
        "question": "How many orders have no items?",
        "gold_sql": (
            "SELECT COUNT(*) FROM orders o WHERE NOT EXISTS (SELECT 1 FROM order_items i WHERE "
            "i.order_id = o.order_id);"
        ),
    },
    {
        "id": "D1",
        "subset": "heldout",
        "kind": "definition",
        "question": (
            "What is the average order value, where the order value is the sum of item price plus "
            "freight value of the order?"
        ),
        "gold_sql": (
            "SELECT ROUND(AVG(v)::numeric, 2) FROM (SELECT order_id, SUM(price + freight_value) "
            "AS v FROM order_items GROUP BY order_id) t;"
        ),
    },
    {
        "id": "R1",
        "subset": "heldout",
        "kind": "ranking",
        "question": (
            "Which 5 product categories have the highest average item price, among categories "
            "with at least 100 items sold? Use the English category name and round the average to "
            "2 decimals."
        ),
        "gold_sql": (
            "SELECT t.product_category_name_english, ROUND(AVG(oi.price)::numeric, 2) FROM "
            "order_items oi JOIN products p ON p.product_id = oi.product_id JOIN "
            "product_category_name_translation t ON t.product_category_name = "
            "p.product_category_name GROUP BY t.product_category_name_english HAVING COUNT(*) >= "
            "100 ORDER BY AVG(oi.price) DESC LIMIT 5;"
        ),
    },
]
