#!/usr/bin/env python3
"""
Scrape Google Play Store reviews for CBE, BOA, and Dashen bank apps.

Usage:
    python scripts/scrape_reviews.py [--per-bank 400] [--output PATH]
"""

import argparse
import sys
from pathlib import Path

# Allow running as script from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import MIN_REVIEWS_PER_BANK, RAW_DATA_DIR, RAW_REVIEWS_CSV, SCRAPE_TARGET_PER_BANK
from src.scraper import scrape_all_banks


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Play Store reviews for Ethiopian bank apps")
    parser.add_argument(
        "--per-bank",
        type=int,
        default=SCRAPE_TARGET_PER_BANK,
        help=f"Raw scrape target per bank (default: {SCRAPE_TARGET_PER_BANK}; min clean: {MIN_REVIEWS_PER_BANK})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=RAW_REVIEWS_CSV,
        help="Output CSV path for raw scraped data",
    )
    args = parser.parse_args()

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Target: {args.per_bank} reviews per bank ({args.per_bank * 3} total minimum)")
    df = scrape_all_banks(target_per_bank=args.per_bank)

    # Save all columns from scrape (preprocessing script will trim)
    df.to_csv(args.output, index=False)

    print(f"\nSaved {len(df)} raw reviews to {args.output}")
    if df.empty:
        print("Warning: no reviews collected. Check network access and Play Store availability.")
        sys.exit(1)
    print("\nPer-bank counts:")
    print(df.groupby("bank").size().to_string())


if __name__ == "__main__":
    main()
