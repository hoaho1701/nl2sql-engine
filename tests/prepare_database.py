"""Create the schema and a tiny seed in a THROWAWAY Postgres, for CI.

DESTRUCTIVE: create_schema drops every table. Refuses to run without ALLOW_DROP_TABLES=1.
"""
import os
from sqlalchemy import text
from app.load_data import create_schema, get_engine

SEED = [
    "INSERT INTO customers VALUES ('c1', 'u1', 1000, 'sao paulo', 'SP')",
    "INSERT INTO orders (order_id, customer_id, order_status) VALUES ('o1', 'c1', 'delivered'), ('o2', 'c1', 'canceled'), ('o3', 'c1', 'shipped')"
]

def main() -> None:
    if os.environ.get("ALLOW_DROP_TABLES") != "1":
        raise SystemExit("Refusing to drop tables: set ALLOW_DROP_TABLES=1 for a throwaway database.")
    engine = get_engine()
    create_schema(engine)
    with engine.begin() as conn:
        for statement in SEED:
            conn.execute(text(statement))
    print("schema created and seeded")

if __name__ == "__main__":
    main()