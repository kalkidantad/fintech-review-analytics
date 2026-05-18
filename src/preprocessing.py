"""Preprocessing utilities for scraped Play Store reviews."""

import pandas as pd


REQUIRED_COLUMNS = ["review", "rating", "date", "bank", "source"]


def normalize_dates(series: pd.Series) -> pd.Series:
    """Normalize review dates to YYYY-MM-DD format."""
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    return parsed.dt.strftime("%Y-%m-%d")


def clean_reviews(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Clean raw scraped reviews.

    - Remove duplicates (by review text + bank)
    - Drop rows missing review text or rating
    - Normalize dates
    - Keep only required output columns

    Returns cleaned DataFrame and a stats dict for documentation.
    """
    stats: dict = {"initial_count": len(df)}

    if df.empty:
        stats["final_count"] = 0
        return pd.DataFrame(columns=REQUIRED_COLUMNS), stats

    working = df.copy()

    # Drop rows with missing critical fields
    missing_review = working["review"].isna() | (working["review"].str.strip() == "")
    missing_rating = working["rating"].isna()
    stats["dropped_missing_review"] = int(missing_review.sum())
    stats["dropped_missing_rating"] = int(missing_rating.sum())
    working = working[~missing_review & ~missing_rating]

    # Normalize rating to integer 1-5
    working["rating"] = pd.to_numeric(working["rating"], errors="coerce")
    invalid_rating = working["rating"].isna() | ~working["rating"].between(1, 5)
    stats["dropped_invalid_rating"] = int(invalid_rating.sum())
    working = working[~invalid_rating]
    working["rating"] = working["rating"].astype(int)

    # Deduplicate: prefer review_id when present, else review text + bank
    before_dedup = len(working)
    if "review_id" in working.columns and working["review_id"].notna().any():
        working = working.drop_duplicates(subset=["review_id"], keep="first")
    working["_review_key"] = (
        working["review"].str.lower().str.strip() + "|" + working["bank"].astype(str)
    )
    working = working.drop_duplicates(subset=["_review_key"], keep="first")
    stats["duplicates_removed"] = before_dedup - len(working)
    drop_cols = [c for c in ("_review_key", "review_id", "app_name") if c in working.columns]
    working = working.drop(columns=drop_cols, errors="ignore")

    # Normalize dates
    if "date" in working.columns:
        working["date"] = normalize_dates(working["date"])
        stats["dropped_invalid_date"] = int(working["date"].isna().sum())
        working = working[working["date"].notna()]

    # Ensure source column
    if "source" not in working.columns:
        working["source"] = "Google Play"
    working["source"] = working["source"].fillna("Google Play")

    # Select output columns
    output = working[REQUIRED_COLUMNS].reset_index(drop=True)
    stats["final_count"] = len(output)
    stats["missing_pct"] = round(
        (stats["initial_count"] - stats["final_count"]) / max(stats["initial_count"], 1)
        * 100,
        2,
    )

    return output, stats


def print_cleaning_report(stats: dict) -> None:
    """Print a human-readable preprocessing summary."""
    print("\n--- Preprocessing Report ---")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print("----------------------------\n")
