from pathlib import Path

import pandas as pd

DATA_DIR = Path("data/raw")

# Columns with at most this many distinct values are treated as "enum-like"
# and have their actual values printed out — useful later for writing table
# descriptions / prompt context (e.g. knowing order_status only ever takes
# a fixed small set of values).
ENUM_LIKE_MAX_UNIQUE = 20


def print_cardinality(df: pd.DataFrame) -> None:
    for column in df.columns:
        nunique = df[column].nunique(dropna=True)
        if nunique <= ENUM_LIKE_MAX_UNIQUE:
            values = sorted(df[column].dropna().unique().tolist())
            print(f"  - {column}: {nunique} distinct -> {values}")
        else:
            print(f"  - {column}: {nunique} distinct")


def print_missing_values(df: pd.DataFrame) -> None:
    # Only show columns that actually have missing values, instead of
    # always printing the top 10 regardless of whether they're zero.
    missing = df.isna().sum()
    missing = missing[missing > 0].sort_values(ascending=False)
    if missing.empty:
        print("  (none)")
    else:
        print(missing.to_string())


def main() -> None:
    csv_files = sorted(DATA_DIR.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {DATA_DIR.resolve()}")

    for path in csv_files:
        df = pd.read_csv(path)

        print("=" * 80)
        print(path.name)
        print("=" * 80)

        print(f"Rows: {len(df):,}")
        print(f"Columns: {len(df.columns)}")

        print("\nColumns:")
        for column in df.columns:
            print(f"  - {column}: {df[column].dtype}")

        print("\nCardinality:")
        print_cardinality(df)

        print("\nMissing values:")
        print_missing_values(df)

        print("\nSample:")
        print(df.head(3).to_string(index=False))

        print()


if __name__ == "__main__":
    main()
