"""Tests for review preprocessing pipeline."""

import pandas as pd
import pytest

from src.preprocessing import REQUIRED_COLUMNS, clean_reviews, normalize_dates


@pytest.fixture
def sample_raw_df():
    return pd.DataFrame(
        {
            "review": [
                "Great app, fast transfers",
                "Great app, fast transfers",  # duplicate
                "",
                "Slow loading during transfer",
                None,
            ],
            "rating": [5, 5, 4, 2, 3],
            "date": ["2024-01-15", "2024-01-15", "2024-02-01", "2024-03-10", "2024-04-01"],
            "bank": ["CBE", "CBE", "BOA", "BOA", "Dashen"],
            "source": ["Google Play"] * 5,
        }
    )


def test_clean_reviews_removes_duplicates_and_empty(sample_raw_df):
    cleaned, stats = clean_reviews(sample_raw_df)
    assert stats["duplicates_removed"] >= 1
    assert stats["dropped_missing_review"] >= 1
    assert len(cleaned) == 2
    assert list(cleaned.columns) == REQUIRED_COLUMNS


def test_clean_reviews_output_columns():
    df = pd.DataFrame(
        {
            "review": ["Good UI"],
            "rating": [5],
            "date": ["2024-06-01T12:00:00Z"],
            "bank": ["CBE"],
            "source": ["Google Play"],
        }
    )
    cleaned, _ = clean_reviews(df)
    assert cleaned["date"].iloc[0] == "2024-06-01"
    assert cleaned["rating"].iloc[0] == 5


def test_normalize_dates_iso_format():
    series = pd.Series(["2023-12-25", "invalid"])
    result = normalize_dates(series)
    assert result.iloc[0] == "2023-12-25"
    assert pd.isna(result.iloc[1]) or result.iloc[1] is None


def test_clean_reviews_invalid_rating_dropped():
    df = pd.DataFrame(
        {
            "review": ["Test", "Test2"],
            "rating": [6, None],
            "date": ["2024-01-01", "2024-01-02"],
            "bank": ["CBE", "CBE"],
            "source": ["Google Play", "Google Play"],
        }
    )
    cleaned, stats = clean_reviews(df)
    assert len(cleaned) == 0
    assert stats["final_count"] == 0
