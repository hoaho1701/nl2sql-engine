"""Create (or refresh) the read-only Postgres role used to execute generated SQL."""

import os

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql


def main() -> None:
    load_dotenv()
    role = sql.Identifier(os.environ["POSTGRES_READONLY_USER"])
    password = sql.Literal(os.environ["POSTGRES_READONLY_PASSWORD"])
    db = sql.Identifier(os.environ["POSTGRES_DB"])

    conn = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %s",
            (os.environ["POSTGRES_READONLY_USER"],),
        )
        verb = "ALTER" if cur.fetchone() else "CREATE"
        # CREATE/ALTER ROLE cannot take bind parameters, so compose the literal safely.
        cur.execute(sql.SQL("{} ROLE {} LOGIN PASSWORD {}").format(sql.SQL(verb), role, password))
        cur.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(db, role))
        cur.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
        cur.execute(sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}").format(role))
        cur.execute(
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {}"
            ).format(role)
        )
    conn.close()
    done = "created" if verb == "CREATE" else "updated"
    print(f"{done} role {os.environ['POSTGRES_READONLY_USER']}")


if __name__ == "__main__":
    main()
