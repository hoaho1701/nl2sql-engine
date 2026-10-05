"""Create (or refresh) the read-only Postgres role used to execute generated SQL.

Run from the repo root, after `docker compose up -d` reports healthy:

    uv run python -m app.create_readonly_role

Safe to run repeatedly: an existing role only has its password and grants refreshed.
The role lives in the Postgres volume, so a fresh volume needs this script again.
"""

import os

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql

from app.vector_store import REPO_ROOT


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    role_name = os.environ["POSTGRES_READONLY_USER"]
    role = sql.Identifier(role_name)
    password = sql.Literal(os.environ["POSTGRES_READONLY_PASSWORD"])
    db = sql.Identifier(os.environ["POSTGRES_DB"])

    conn = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
    )
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role_name,))
            verb = "ALTER" if cur.fetchone() else "CREATE"
            # CREATE/ALTER ROLE cannot take bind parameters, so compose the literal safely.
            cur.execute(
                sql.SQL("{} ROLE {} LOGIN PASSWORD {}").format(sql.SQL(verb), role, password)
            )
            cur.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(db, role))
            cur.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
            cur.execute(sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}").format(role))
            cur.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {}"
                ).format(role)
            )
    finally:
        conn.close()
    done = "created" if verb == "CREATE" else "updated"
    print(f"{done} role {role_name}")


if __name__ == "__main__":
    main()
