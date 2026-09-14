"""Explore raw Olist CSVs before loading: dtypes, cardinality, null ratios, samples."""

from pathlib import Path

import pandas as pd

RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# Below this many distinct values, a column is flagged as a likely enum —
# just a heuristic to guide manual review, not a hard rule.
ENUM_CARDINALITY_THRESHOLD = 20


def inspect_csv(csv_path: Path) -> None:
    """Print dtype, cardinality, null ratio, and sample rows for a CSV."""
    df = pd.read_csv(csv_path)

    print(f"\n{'=' * 80}")
    print(f"{csv_path.name}  ({len(df)} rows, {len(df.columns)} columns)")
    print("=" * 80)

    for col in df.columns:
        dtype = df[col].dtype
        n_unique = df[col].nunique(dropna=True)
        null_ratio = df[col].isna().mean()
        enum_flag = " <- possible enum" if n_unique <= ENUM_CARDINALITY_THRESHOLD else ""
        print(
            f"  {col:<40} dtype={str(dtype):<10} "
            f"unique={n_unique:<8} null={null_ratio:.1%}{enum_flag}"
        )

    print("\n  Sample rows:")
    print(df.head(3).to_string(index=False))


def main() -> None:
    """Run inspect_csv over every file in data/raw/."""
    csv_files = sorted(RAW_DATA_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {RAW_DATA_DIR}")

    for csv_path in csv_files:
        inspect_csv(csv_path)


if __name__ == "__main__":
    main()
