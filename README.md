# Fintech Review Analytics

Customer experience analytics pipeline for **Commercial Bank of Ethiopia (CBE)**, **Bank of Abyssinia (BOA)**, and **Dashen Bank** mobile apps.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Task 1: Data collection & preprocessing

### Apps scraped

| Bank | App name | Play Store package ID |
|------|----------|------------------------|
| CBE | Commercial Bank of Ethiopia Mobile | `com.combanketh.mobilebanking` |
| BOA | BoA Mobile | `com.boa.boaMobileBanking` |
| Dashen | Dashen Mobile | `com.cr2.amolelight` |

### Methodology

- **Library:** [`google-play-scraper`](https://github.com/JoMingyu/google-play-scraper)
- **Fields:** `review`, `rating`, `date`, `bank`, `source` (`Google Play`)
- **Locale:** `lang=en`, `country=et`
- **Target:** ≥400 reviews per bank (≥1,200 total)

### Run pipeline

```bash
python scripts/scrape_reviews.py
python scripts/preprocess_reviews.py
```

Outputs: `data/raw/reviews_raw.csv`, `data/processed/reviews_clean.csv` (gitignored).

### Limitations

- Play Store API may cap available history per app.
- Scraped CSV files must not be committed.

## Testing

```bash
pytest tests/ -v
```
