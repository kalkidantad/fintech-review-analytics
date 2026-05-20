"""Tests for Task 4 insight aggregation helpers."""

import pandas as pd

from src.insights_metrics import build_bank_insights, cross_bank_summary, recommendations_for_bank


def _tiny_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "bank": ["CBE"] * 8 + ["BOA"] * 8,
            "rating": [5, 5, 4, 4, 3, 2, 1, 1] * 2,
            "sentiment_label": [
                "positive",
                "positive",
                "positive",
                "neutral",
                "neutral",
                "negative",
                "negative",
                "negative",
            ]
            * 2,
            "identified_theme": [
                "UI & Design",
                "UI & Design",
                "Transaction Performance",
                "Feature Requests",
                "Feature Requests",
                "Account Access Issues",
                "Account Access Issues",
                "Transaction Performance",
            ]
            * 2,
            "review_text": [
                "great ui easy navigation",
                "clean design love it",
                "transfer works well",
                "need dark mode",
                "add loans please",
                "otp never arrives",
                "cannot login today",
                "app crashes on transfer",
            ]
            * 2,
        }
    )


def test_cross_bank_summary_smoke():
    df = _tiny_frame()
    out = cross_bank_summary(df)
    assert set(out["bank"]) == {"BOA", "CBE"}
    assert (out["n"] == 8).all()


def test_build_bank_insights_returns_drivers_and_pains():
    df = _tiny_frame()
    ins = build_bank_insights(df, "CBE")
    assert ins["n"] == 8
    assert len(ins["drivers"]) >= 1
    assert len(ins["pains"]) >= 1
    recs = recommendations_for_bank(ins)
    assert len(recs) >= 1
