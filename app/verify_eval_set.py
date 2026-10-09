"""Re-check the new eval cases against the CSV files with pandas.

For every case with a check below, two independent computations must agree: the gold SQL run on
Postgres and a pandas calculation from data/raw. For each "fanout" case a tempting naive join is
also run, and it must give a DIFFERENT result: that difference is what makes the case a real trap.
The version-2 ("core") cases are not covered here.

Needs Postgres running with the data loaded, and data/raw/*.csv.
Run: uv run python -m app.verify_eval_set
"""

import sys
from decimal import Decimal

import pandas as pd

from app.eval_test_set import EVAL_CASES
from app.sql_executor import run_sql_safe
from app.vector_store import REPO_ROOT

RAW = REPO_ROOT / "data" / "raw"
MAX_ROWS = 100_000
TIMEOUT_SECONDS = 120

TRANSLATION = "product_category_name_translation"


def _load() -> dict[str, pd.DataFrame]:
    d = {
        "cus": pd.read_csv(RAW / "olist_customers_dataset.csv"),
        "sel": pd.read_csv(RAW / "olist_sellers_dataset.csv"),
        "tr": pd.read_csv(RAW / f"{TRANSLATION}.csv"),
        "geo": pd.read_csv(RAW / "olist_geolocation_dataset.csv"),
        "prod": pd.read_csv(RAW / "olist_products_dataset.csv"),
        "orders": pd.read_csv(RAW / "olist_orders_dataset.csv"),
        "items": pd.read_csv(RAW / "olist_order_items_dataset.csv"),
        "pay": pd.read_csv(RAW / "olist_order_payments_dataset.csv"),
        "rev": pd.read_csv(RAW / "olist_order_reviews_dataset.csv"),
    }
    for column in (
        "order_purchase_timestamp",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ):
        d["orders"][column] = pd.to_datetime(d["orders"][column])
    return d


def _r2(x) -> float:
    return round(float(x), 2)


def _r4(x) -> float:
    return round(float(x), 4)


def _orders_with_multiple_items(d) -> set:
    sizes = d["items"].groupby("order_id").size()
    return set(sizes[sizes > 1].index)


def _f1(d):
    categories = d["prod"].merge(d["tr"], on="product_category_name")
    ids = categories[categories.product_category_name_english == "health_beauty"].product_id
    orders = set(d["items"][d["items"].product_id.isin(ids)].order_id)
    return [(_r2(d["pay"][d["pay"].order_id.isin(orders)].payment_value.sum()),)]


def _f3(d):
    orders = set(d["pay"][d["pay"].payment_type == "credit_card"].order_id)
    return [(_r2(d["items"][d["items"].order_id.isin(orders)].freight_value.sum()),)]


def _f4(d):
    pay = d["pay"][d["pay"].order_id.isin(_orders_with_multiple_items(d))]
    return [(_r2(pay.groupby("order_id").payment_value.sum().mean()),)]


def _f5(d):
    orders = set(d["rev"][d["rev"].review_score == 5].order_id)
    return [(_r2(d["items"][d["items"].order_id.isin(orders)].price.sum()),)]


def _f6(d):
    zips = set(d["geo"].geolocation_zip_code_prefix)
    return [(int(d["cus"].customer_zip_code_prefix.isin(zips).sum()),)]


def _f7(d):
    zips = set(d["geo"].geolocation_zip_code_prefix)
    return [(int(d["sel"].seller_zip_code_prefix.isin(zips).sum()),)]


def _f8(d):
    per_zip = (
        d["geo"]
        .groupby("geolocation_zip_code_prefix")[["geolocation_lat", "geolocation_lng"]]
        .mean()
        .reset_index()
    )
    rj = d["cus"][d["cus"].customer_state == "RJ"]
    merged = rj.merge(
        per_zip, left_on="customer_zip_code_prefix", right_on="geolocation_zip_code_prefix"
    )
    return [(_r4(merged.geolocation_lat.mean()), _r4(merged.geolocation_lng.mean()))]


def _f9(d):
    orders = set(d["pay"][d["pay"].payment_type == "voucher"].order_id)
    return [(int(d["items"].order_id.isin(orders).sum()),)]


def _f10(d):
    rj_sellers = set(d["sel"][d["sel"].seller_state == "RJ"].seller_id)
    orders = set(d["items"][d["items"].seller_id.isin(rj_sellers)].order_id)
    return [(_r2(d["pay"][d["pay"].order_id.isin(orders)].payment_value.sum()),)]


def _f11(d):
    orders = set(d["pay"][d["pay"].payment_installments > 5].order_id)
    return [(_r2(d["items"][d["items"].order_id.isin(orders)].price.mean()),)]


def _f12(d):
    return [(int(d["rev"].order_id.isin(_orders_with_multiple_items(d)).sum()),)]


def _c1(d):
    merged = d["pay"].merge(d["orders"][["order_id", "customer_id"]], on="order_id")
    merged = merged.merge(d["cus"][["customer_id", "customer_state"]], on="customer_id")
    return [(_r2(merged[merged.customer_state == "SP"].payment_value.sum()),)]


def _c2(d):
    voucher_orders = d["pay"][d["pay"].payment_type == "voucher"][["order_id"]].drop_duplicates()
    merged = d["orders"][["order_id", "customer_id"]].merge(voucher_orders, on="order_id")
    merged = merged.merge(d["cus"], on="customer_id")
    return [(int(merged.customer_unique_id.nunique()),)]


def _n1(d):
    return [(int((~d["orders"].order_id.isin(set(d["items"].order_id))).sum()),)]


def _n3(d):
    o = d["orders"]
    return [(int(((o.order_status == "delivered") & o.order_delivered_customer_date.isna()).sum()),)]


def _n4(d):
    return [(_r2(d["prod"][d["prod"].product_category_name.isna()].product_weight_g.mean()),)]


def _n5(d):
    return [(int(d["orders"].order_approved_at.isna().sum()),)]


def _d1(d):
    items = d["items"]
    return [(_r2((items.price + items.freight_value).groupby(items.order_id).sum().mean()),)]


def _d2(d):
    o = d["orders"]
    merged = o[o.order_purchase_timestamp.dt.year == 2017].merge(d["cus"], on="customer_id")
    return [(int(merged.customer_unique_id.nunique()),)]


def _d3(d):
    o = d["orders"]
    delivered = o[(o.order_status == "delivered") & o.order_delivered_customer_date.notna()]
    late = (delivered.order_delivered_customer_date > delivered.order_estimated_delivery_date).sum()
    return [(_r2(100.0 * late / len(delivered)),)]


def _r1(d):
    merged = d["items"].merge(d["prod"][["product_id", "product_category_name"]], on="product_id")
    merged = merged.merge(d["tr"], on="product_category_name")
    stats = merged.groupby("product_category_name_english").price.agg(["mean", "size"])
    ranked = stats[stats["size"] >= 100].sort_values("mean", ascending=False)["mean"]
    assert round(ranked.iloc[4], 2) != round(ranked.iloc[5], 2), "tie at the 5th place"
    return sorted((name, _r2(value)) for name, value in ranked.head(5).items())


def _r3(d):
    counts = d["items"].groupby("seller_id").order_id.nunique().sort_values(ascending=False)
    assert counts.iloc[4] != counts.iloc[5], "tie at the 5th place"
    return sorted((seller, int(n)) for seller, n in counts.head(5).items())


PANDAS_CHECKS = {
    "F1": _f1, "F3": _f3, "F4": _f4, "F5": _f5, "F6": _f6, "F7": _f7, "F8": _f8, "F9": _f9,
    "F10": _f10, "F11": _f11, "F12": _f12, "C1": _c1, "C2": _c2, "N1": _n1, "N3": _n3,
    "N4": _n4, "N5": _n5, "D1": _d1, "D2": _d2, "D3": _d3, "R1": _r1, "R3": _r3,
}

# The tempting wrong query for each fanout case: it joins two "many" sides and multiplies rows.
NAIVE_SQL = {
    "F1": (
        "SELECT ROUND(SUM(p.payment_value)::numeric, 2) FROM order_payments p "
        "JOIN order_items oi ON oi.order_id = p.order_id "
        "JOIN products pr ON pr.product_id = oi.product_id "
        f"JOIN {TRANSLATION} t ON t.product_category_name = pr.product_category_name "
        "WHERE t.product_category_name_english = 'health_beauty'"
    ),
    "F3": (
        "SELECT ROUND(SUM(oi.freight_value)::numeric, 2) FROM order_items oi "
        "JOIN order_payments p ON p.order_id = oi.order_id WHERE p.payment_type = 'credit_card'"
    ),
    "F4": (
        "SELECT ROUND(AVG(p.payment_value)::numeric, 2) FROM order_payments p "
        "JOIN order_items oi ON oi.order_id = p.order_id WHERE p.order_id IN "
        "(SELECT order_id FROM order_items GROUP BY order_id HAVING COUNT(*) > 1)"
    ),
    "F5": (
        "SELECT ROUND(SUM(oi.price)::numeric, 2) FROM order_items oi "
        "JOIN order_reviews r ON r.order_id = oi.order_id WHERE r.review_score = 5"
    ),
    "F6": (
        "SELECT COUNT(*) FROM customers c "
        "JOIN geolocation g ON g.geolocation_zip_code_prefix = c.customer_zip_code_prefix"
    ),
    "F7": (
        "SELECT COUNT(*) FROM sellers s "
        "JOIN geolocation g ON g.geolocation_zip_code_prefix = s.seller_zip_code_prefix"
    ),
    "F8": (
        "SELECT ROUND(AVG(g.geolocation_lat)::numeric, 4), ROUND(AVG(g.geolocation_lng)::numeric, 4) "
        "FROM customers c JOIN geolocation g "
        "ON g.geolocation_zip_code_prefix = c.customer_zip_code_prefix "
        "WHERE c.customer_state = 'RJ'"
    ),
    "F9": (
        "SELECT COUNT(*) FROM order_items oi "
        "JOIN order_payments p ON p.order_id = oi.order_id WHERE p.payment_type = 'voucher'"
    ),
    "F10": (
        "SELECT ROUND(SUM(p.payment_value)::numeric, 2) FROM order_payments p "
        "JOIN order_items i ON i.order_id = p.order_id "
        "JOIN sellers s ON s.seller_id = i.seller_id WHERE s.seller_state = 'RJ'"
    ),
    "F11": (
        "SELECT ROUND(AVG(i.price)::numeric, 2) FROM order_items i "
        "JOIN order_payments p ON p.order_id = i.order_id WHERE p.payment_installments > 5"
    ),
    "F12": (
        "SELECT COUNT(*) FROM order_reviews r JOIN order_items i ON i.order_id = r.order_id "
        "WHERE r.order_id IN (SELECT order_id FROM order_items GROUP BY order_id HAVING COUNT(*) > 1)"
    ),
}


def _normalize(rows) -> list:
    """Sort the rows and turn numbers into floats rounded to 4 places, so results are comparable."""
    return sorted(
        tuple(round(float(v), 4) if isinstance(v, (Decimal, float)) else v for v in row)
        for row in rows
    )


def _run(sql: str) -> list:
    return run_sql_safe(sql, max_rows=MAX_ROWS, timeout_seconds=TIMEOUT_SECONDS)[1]


def verify() -> list[str]:
    """Check every case that has a pandas check. Return a list of problems (empty if all is well)."""
    data = _load()
    problems = []
    for case in EVAL_CASES:
        case_id = case["id"]
        if case_id not in PANDAS_CHECKS:
            continue
        gold = _normalize(_run(case["gold_sql"]))
        expected = _normalize(PANDAS_CHECKS[case_id](data))
        status = "OK" if gold == expected else "MISMATCH"
        line = f"{case_id:<4} {case['subset']:<8} {case['kind']:<10} gold vs pandas: {status}"
        if gold != expected:
            problems.append(f"{case_id}: gold {gold[:2]} but pandas {expected[:2]}")
        if case_id in NAIVE_SQL:
            naive = _normalize(_run(NAIVE_SQL[case_id]))
            trap = "differs (real trap)" if naive != gold else "SAME (not a trap)"
            line += f" | naive join: {trap}"
            if naive == gold:
                problems.append(f"{case_id}: the naive join gives the same result, so it is not a trap")
        print(line)
    return problems


def main() -> None:
    problems = verify()
    print()
    if problems:
        print("PROBLEMS:")
        for problem in problems:
            print(" -", problem)
        sys.exit(1)
    print("all checked cases agree")


if __name__ == "__main__":
    main()
