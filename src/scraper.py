"""Google Play Store review scraper for Ethiopian bank mobile apps."""

import time
from datetime import datetime
from typing import Any

import pandas as pd
from google_play_scraper import Sort, reviews

from src.config import (
    BANK_APPS,
    MIN_REVIEWS_PER_BANK,
    REVIEWS_PER_BATCH,
    SCRAPE_TARGET_PER_BANK,
    SOURCE_LABEL,
)


def fetch_reviews_for_app(
    package_id: str,
    app_name: str,
    bank_label: str,
    target_count: int = MIN_REVIEWS_PER_BANK,
    lang: str = "en",
    country: str = "et",
    sleep_seconds: float = 1.0,
) -> list[dict[str, Any]]:
    """
    Fetch reviews from Google Play Store with pagination.

    Uses NEWEST sort first, then falls back to MOST_RELEVANT if needed
    to reach the target review count.
    """
    collected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    # Single sort order avoids heavy overlap; fall back only if quota not met
    sort_orders = [Sort.NEWEST, Sort.MOST_RELEVANT]

    for sort_order in sort_orders:
        if len(collected) >= target_count:
            break
        continuation_token = None
        while len(collected) < target_count:
            batch, continuation_token = reviews(
                package_id,
                lang=lang,
                country=country,
                sort=sort_order,
                count=REVIEWS_PER_BATCH,
                continuation_token=continuation_token,
            )
            if not batch:
                break

            for item in batch:
                review_id = item.get("reviewId") or item.get("review_id")
                if review_id:
                    if review_id in seen_ids:
                        continue
                    seen_ids.add(review_id)

                review_date = item.get("at")
                if isinstance(review_date, datetime):
                    date_str = review_date.strftime("%Y-%m-%d")
                else:
                    date_str = str(review_date)[:10] if review_date else None

                collected.append(
                    {
                        "review": (item.get("content") or "").strip(),
                        "rating": item.get("score"),
                        "date": date_str,
                        "bank": bank_label,
                        "app_name": app_name,
                        "source": SOURCE_LABEL,
                        "review_id": review_id,
                    }
                )
                if len(collected) >= target_count:
                    break

            if continuation_token is None:
                break
            time.sleep(sleep_seconds)

    return collected[:target_count]


def scrape_all_banks(
    target_per_bank: int = SCRAPE_TARGET_PER_BANK,
) -> pd.DataFrame:
    """Scrape reviews for all configured bank apps and return a DataFrame."""
    all_rows: list[dict[str, Any]] = []

    for bank_key, app_info in BANK_APPS.items():
        print(f"Scraping {bank_key} ({app_info['app_name']})...")
        rows = fetch_reviews_for_app(
            package_id=app_info["package_id"],
            app_name=app_info["app_name"],
            bank_label=app_info["bank_label"],
            target_count=target_per_bank,
        )
        print(f"  Collected {len(rows)} reviews for {bank_key}")
        all_rows.extend(rows)
        time.sleep(2.0)

    return pd.DataFrame(all_rows)
