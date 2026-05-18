#!/usr/bin/env python3
"""
Preprocess raw scraped reviews into a clean analysis-ready CSV.

Usage:
    python scripts/preprocess_reviews.py [--input PATH] [--output PATH]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import CLEAN_REVIEWS_CSV, PROCESSED_DATA_DIR, RAW_REVIEWS_CSV
from src.preprocessing import clean_reviews, print_cleaning_report
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean and normalize scraped reviews")
    parser.add_argument("--input", type=Path, default=RAW_REVIEWS_CSV)
    parser.add_argument("--output", type=Path, default=CLEAN_REVIEWS_CSV)
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: input file not found: {args.input}")
        print("Run scripts/scrape_reviews.py first.")
        sys.exit(1)

    df = pd.read_csv(args.input)
    cleaned, stats = clean_reviews(df)
    print_cleaning_report(stats)

    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(args.output, index=False)

    print(f"Saved {len(cleaned)} cleaned reviews to {args.output}")
    print("\nPer-bank counts:")
    print(cleaned.groupby("bank").size().to_string())


if __name__ == "__main__":
    main()
