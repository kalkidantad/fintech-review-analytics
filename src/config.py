"""Configuration for Ethiopian fintech app review analytics."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
ANALYSIS_DATA_DIR = PROJECT_ROOT / "data" / "analysis"

# Google Play package IDs and display names for the three banks
BANK_APPS = {
    "CBE": {
        "package_id": "com.combanketh.mobilebanking",
        "app_name": "Commercial Bank of Ethiopia Mobile",
        "bank_label": "CBE",
    },
    "BOA": {
        "package_id": "com.boa.boaMobileBanking",
        "app_name": "BoA Mobile",
        "bank_label": "BOA",
    },
    "Dashen": {
        "package_id": "com.cr2.amolelight",
        "app_name": "Dashen Mobile",
        "bank_label": "Dashen",
    },
}

SOURCE_LABEL = "Google Play"
MIN_REVIEWS_PER_BANK = 400
# Scrape extra to absorb text-level duplicates after preprocessing
SCRAPE_TARGET_PER_BANK = 550
# Scrape extra raw rows to offset duplicate removal during preprocessing (~25%)
SCRAPE_TARGET_PER_BANK = 550
REVIEWS_PER_BATCH = 200

# Output filenames (gitignored via data/ and *.csv rules)
RAW_REVIEWS_CSV = RAW_DATA_DIR / "reviews_raw.csv"
CLEAN_REVIEWS_CSV = PROCESSED_DATA_DIR / "reviews_clean.csv"
SENTIMENT_CSV = ANALYSIS_DATA_DIR / "reviews_sentiment.csv"
