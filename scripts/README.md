# Scripts

| Script | Purpose |
|--------|---------|
| `scrape_reviews.py` | Fetch reviews from Google Play for CBE, BOA, and Dashen |
| `preprocess_reviews.py` | Clean raw data → `data/processed/reviews_clean.csv` |
| `run_sentiment_analysis.py` | DistilBERT sentiment + theme labels → `data/analysis/reviews_sentiment.csv` |

Run from project root:

```bash
python scripts/scrape_reviews.py
python scripts/preprocess_reviews.py
python scripts/run_sentiment_analysis.py
```
