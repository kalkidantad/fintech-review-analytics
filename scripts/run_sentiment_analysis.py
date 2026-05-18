#!/usr/bin/env python3
"""
Run sentiment and thematic analysis on cleaned reviews.

Outputs CSV with: review_id, review_text, sentiment_label, sentiment_score, identified_theme
(plus bank, rating, date for downstream use).

Usage:
    python scripts/run_sentiment_analysis.py [--input PATH] [--output PATH]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.config import ANALYSIS_DATA_DIR, CLEAN_REVIEWS_CSV, SENTIMENT_CSV
from src.sentiment import (
    add_sentiment_columns,
    aggregate_sentiment_by_bank,
    aggregate_sentiment_by_rating,
)
from src.themes import add_theme_column, extract_themes_per_bank


def main() -> None:
    parser = argparse.ArgumentParser(description="Sentiment and thematic analysis pipeline")
    parser.add_argument("--input", type=Path, default=CLEAN_REVIEWS_CSV)
    parser.add_argument("--output", type=Path, default=SENTIMENT_CSV)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument(
        "--backend",
        choices=["distilbert", "vader"],
        default="distilbert",
        help="Sentiment model: distilbert (default) or vader (faster, no model download)",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: input not found: {args.input}")
        print("Run scrape + preprocess first.")
        sys.exit(1)

    df = pd.read_csv(args.input)
    print(f"Loaded {len(df)} reviews from {args.input}")

    # Assign stable review IDs
    df = df.reset_index(drop=True)
    df["review_id"] = df.index + 1

    print(f"Running {args.backend} sentiment analysis...")
    analyzed = add_sentiment_columns(
        df, batch_size=args.batch_size, backend=args.backend
    )
    analyzed = add_theme_column(analyzed)

    # Task 2 output columns
    output_cols = [
        "review_id",
        "review",
        "sentiment_label",
        "sentiment_score",
        "identified_theme",
        "bank",
        "rating",
        "date",
        "vader_compound",
    ]
    result = analyzed[output_cols].rename(columns={"review": "review_text"})

    ANALYSIS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(f"\nSaved analysis to {args.output}")

    print("\n--- Sentiment by bank ---")
    print(aggregate_sentiment_by_bank(analyzed).to_string(index=False))

    print("\n--- Sentiment by bank & star rating (sample) ---")
    by_rating = aggregate_sentiment_by_rating(analyzed)
    print(by_rating.head(15).to_string(index=False))

    print("\n--- Theme distribution per bank ---")
    theme_report = extract_themes_per_bank(analyzed)
    for bank, info in theme_report.items():
        print(f"\n{bank} ({info['review_count']} reviews):")
        print("  Top keywords:", [k[0] for k in info["top_keywords"][:8]])
        print("  Themes:", info["theme_distribution"])


if __name__ == "__main__":
    main()
