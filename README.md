# Fintech Review Analytics

Customer experience analytics pipeline for **Commercial Bank of Ethiopia (CBE)**, **Bank of Abyssinia (BOA)**, and **Dashen Bank** mobile apps. Scrapes Google Play reviews, preprocesses them, and runs sentiment and thematic analysis for Omega Consultancy.

## Project structure

```
fintech-review-analytics/
├── data/raw/              # Raw scraped CSV (gitignored)
├── data/processed/        # Cleaned reviews (gitignored)
├── data/analysis/         # Sentiment + themes output (gitignored)
├── scripts/               # CLI entry points
├── src/                   # Reusable modules
├── tests/                 # Unit tests
└── notebooks/             # Exploratory analysis & report
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# CPU-only PyTorch (recommended for DistilBERT on laptops/CI):
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

## Task 1: Data collection & preprocessing

### Apps scraped

| Bank | App name | Play Store package ID |
|------|----------|------------------------|
| CBE | Commercial Bank of Ethiopia Mobile | `com.combanketh.mobilebanking` |
| BOA | BoA Mobile | `com.boa.boaMobileBanking` |
| Dashen | Dashen Mobile | `com.cr2.amolelight` |

### Methodology

- **Library:** [`google-play-scraper`](https://github.com/JoMingyu/google-play-scraper) (Python)
- **Fields:** `review`, `rating` (1–5), `date`, `bank`, `source` (`Google Play`)
- **Sort order:** `NEWEST` first, then `MOST_RELEVANT` if needed to reach 400+ reviews per bank
- **Locale:** `lang=en`, `country=et` (Ethiopia Play Store; includes English and Amharic reviews)
- **Batch size:** 200 reviews per API call with 1s delay between pages to reduce rate-limit risk
- **Target:** ≥400 reviews per bank (≥1,200 total)

### Preprocessing

`scripts/preprocess_reviews.py` applies:

1. Drop rows missing review text or rating
2. Validate ratings in 1–5
3. Remove duplicates by `review_id`, then identical review text per bank
4. Normalize dates to `YYYY-MM-DD`
5. Output columns: `review`, `rating`, `date`, `bank`, `source`

### Run pipeline

```bash
python scripts/scrape_reviews.py
python scripts/preprocess_reviews.py
```

Outputs:

- `data/raw/reviews_raw.csv`
- `data/processed/reviews_clean.csv`

### Collection results (latest run)

| Bank | Raw scraped | After cleaning |
|------|-------------|----------------|
| CBE | 650 | 466 |
| BOA | 650 | 517 |
| Dashen | 505* | 397 |
| **Total** | **1,805** | **1,380** |

\*Dashen Mobile returns fewer than 650 reviews via the Play Store API (store listing cap).

### Limitations

- Play Store API may cap available history per app (observed for Dashen).
- Reviews are user-generated and may mix **English, Amharic, and other languages**; NLP models are English-centric.
- Scraped CSV files are **gitignored** and must not be committed.

## Task 2: Sentiment & thematic analysis

### Sentiment

- **Primary model:** `distilbert-base-uncased-finetuned-sst-2-english` (Hugging Face transformers)
- **Output:** `sentiment_label` (`positive` / `negative` / `neutral`), `sentiment_score` (model confidence)
- **Neutral class:** SST-2 is binary; scores between 0.45–0.55 are mapped to `neutral`
- **Comparison:** `vader_compound` column for lexicon-based comparison

**Rationale:** DistilBERT aligns better with nuanced review language than lexicon-only tools. VADER is retained for quick baseline comparison via `--backend vader`.

### Themes

- **Keywords:** TF-IDF unigrams and bigrams (`sklearn`)
- **Themes (5):** Account Access Issues, Transaction Performance, UI & Design, Customer Support, Feature Requests
- **Assignment:** Keyword overlap scoring per review (`src/themes.py`)

### Run analysis

```bash
# DistilBERT (downloads ~250MB model on first run)
python scripts/run_sentiment_analysis.py --backend distilbert

# VADER lexicon (fast)
python scripts/run_sentiment_analysis.py --backend vader
```

Output: `data/analysis/reviews_sentiment.csv` with columns  
`review_id`, `review_text`, `sentiment_label`, `sentiment_score`, `identified_theme`, plus `bank`, `rating`, `date`, `vader_compound`.

Set `HF_HOME=.cache/huggingface` to cache the transformer model locally.

## Testing & CI

```bash
pytest tests/ -v
```

GitHub Actions runs `pip install -r requirements.txt` and `pytest` on every push to `main`.

## Business scenarios (preview)

| Scenario | Analysis approach |
|----------|-------------------|
| Slow loading / transfers | Theme **Transaction Performance** + keywords `slow`, `transfer`, `loading` |
| Feature requests | Theme **Feature Requests** + TF-IDF top terms per bank |
| Recurring complaints | Theme **Account Access Issues** (`login`, `otp`, `password`) |

## License

Educational project — 10 Academy Week 2 challenge.
