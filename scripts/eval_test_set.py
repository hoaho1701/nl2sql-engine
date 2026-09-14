# Mỗi test case: 1 câu hỏi tiếng Anh + 1 câu SQL "đáp án đúng" tự viết tay (gold_sql).
# gold_sql dùng để CHẠY lấy kết quả đúng, không so sánh trực tiếp (so text) với SQL do LLM sinh ra.
from sql_executor import run_sql_safe

TEST_CASES = [
    {
        "question": "How many orders were delivered?",
        "gold_sql": "SELECT COUNT(*) FROM orders WHERE order_status = 'delivered'",
    },
    {
        "question": "What is the average review score of orders paid by credit card?",
        "gold_sql": "SELECT AVG(review_score) FROM order_reviews WHERE order_id IN (SELECT order_id FROM order_payments WHERE payment_type='credit_card')",
    },
    {
        "question": "Which product category name has the highest number of unique orders?",
        "gold_sql": "SELECT p.product_category_name FROM products p JOIN order_items i ON p.product_id = i.product_id GROUP BY p.product_category_name ORDER BY COUNT(DISTINCT i.order_id) DESC LIMIT 1",
    },
    {
        "question": "How many products do not have a category name assigned?",
        "gold_sql": "SELECT COUNT(*) FROM products WHERE product_category_name IS NULL",
    },
    {
        "question": "What is the total number of orders placed by customers whose zip code exists in the geolocation table?",
        "gold_sql": "SELECT COUNT(o.order_id) FROM orders o JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_zip_code_prefix IN (SELECT DISTINCT geolocation_zip_code_prefix FROM geolocation)",
    },
    {
        "question": "How many sellers have sold more than 100 items in total?",
        "gold_sql": "SELECT COUNT(*) FROM (SELECT seller_id FROM order_items GROUP BY seller_id HAVING COUNT(order_item_id) > 100)",
    },
    {
        "question": "What is the total revenue (price plus freight value) for all delivered orders?",
        "gold_sql": "SELECT SUM(i.price + i.freight_value) FROM order_items i JOIN orders o ON i.order_id = o.order_id WHERE o.order_status = 'delivered'",
    },
    {
        "question": "How many orders were purchased in the year 2018?",
        "gold_sql": "SELECT COUNT(*) FROM orders WHERE strftime('%Y', order_purchase_timestamp) = '2018'",
    },
    {
        "question": "What is the unique customer id of the person who spent the most money on product prices in total?",
        "gold_sql": "SELECT c.customer_unique_id FROM customers c JOIN orders o ON c.customer_id = o.customer_id JOIN order_items i ON o.order_id = i.order_id GROUP BY c.customer_unique_id ORDER BY SUM(i.price) DESC LIMIT 1",
    },
    {
        "question": "How many delivered orders reached the customer after the estimated delivery date?",
        "gold_sql": "SELECT COUNT(*) FROM orders WHERE order_status = 'delivered' AND order_delivered_customer_date > order_estimated_delivery_date",
    },
    {
        "question": "How many items were sold in the English product category 'health_beauty'?",
        "gold_sql": "SELECT COUNT(i.order_item_id) FROM order_items i JOIN products p ON i.product_id = p.product_id JOIN product_category_name_translation t ON p.product_category_name = t.product_category_name WHERE t.product_category_name_english = 'health_beauty'",
    },
    # 4 case thêm sau, nhắm vào 2 khoảng trống: chưa case nào trả về nhiều dòng
    # thật (stress-test Counter/so sánh bỏ qua thứ tự), và bảng sellers/order_reviews
    # chưa từng được động tới trực tiếp.
    {
        "question": "What are all the distinct payment types used?",
        "gold_sql": "SELECT DISTINCT payment_type FROM order_payments",
    },
    {
        "question": "How many orders are there for each order status?",
        "gold_sql": "SELECT order_status, COUNT(*) FROM orders GROUP BY order_status",
    },
    {
        "question": "How many sellers are located in the state of SP?",
        "gold_sql": "SELECT COUNT(*) FROM sellers WHERE seller_state = 'SP'",
    },
    {
        "question": "How many order reviews have no comment message written?",
        "gold_sql": "SELECT COUNT(*) FROM order_reviews WHERE review_comment_message IS NULL",
    },
]

if __name__ == "__main__":
    for case in TEST_CASES:
        question = case["question"]
        sql = case["gold_sql"]
        try:
            result = run_sql_safe(sql)
            print(f"[{question}] OK -> {result}")
        except Exception as e:
            print(f"[{question}] {type(e).__name__}: {e}")