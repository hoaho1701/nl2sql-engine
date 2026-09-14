"""Load the 9 Olist CSVs into Postgres with real foreign keys."""

TABLE_NAME_MAP = {
    # TODO: CSV filename -> table name
}

DATE_COLUMN_BY_TABLE = {
    # TODO: explicit date columns per table (don't guess from column names)
}


def get_engine():
    """Create a SQLAlchemy engine for Postgres, reading connection info from .env."""
    raise NotImplementedError


def create_schema(engine) -> None:
    """Create the 9 tables with real FKs, in dependency order."""
    raise NotImplementedError


def load_csv_to_table(engine, csv_path: str, table_name: str) -> None:
    """Read a CSV, convert date columns, and append rows into an existing table."""
    raise NotImplementedError


def verify_row_counts(engine) -> None:
    """Compare len(df) per CSV against SELECT COUNT(*) in Postgres."""
    raise NotImplementedError


def main() -> None:
    """create_schema -> load_csv_to_table for all 9 tables -> verify_row_counts."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
