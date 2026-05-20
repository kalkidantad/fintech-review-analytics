# Interim Report — Week 2

**Course:** 10 Academy · Artificial Intelligence Mastery  
**Project:** Customer Experience Analytics for Fintech Apps  
**Client context:** Omega Consultancy — Ethiopian mobile banking (CBE, BOA, Dashen)  
**Reporting period:** Interim submission (Tasks 1 & 2)

---

## 1. Business Objective

The objective of this project is to transform unstructured Google Play Store reviews into actionable product intelligence for three Ethiopian banks: **Commercial Bank of Ethiopia (CBE)**, **Bank of Abyssinia (BOA)**, and **Dashen Bank**. Mobile banking adoption is accelerating, and user reviews provide an unfiltered signal of satisfaction, friction, and unmet needs. Left unanalyzed, this feedback is noise; processed systematically, it becomes a competitive asset for product and customer-experience teams.

The interim phase combines:

- Web scraping and data engineering (Play Store reviews)
- Sentiment classification at scale
- Thematic (keyword and category) analysis
- Bank-level benchmarking and scenario-aligned insights

The broader goal is to give product managers an evidence-backed view of what users praise, what frustrates them, and what to prioritize next.

The analysis was guided by three consulting scenarios:

| Scenario | Business question |
|----------|-------------------|
| **Retaining users** | Is slow loading during transfers a systemic issue across all three apps? |
| **Enhancing features** | What features do users request (e.g., fingerprint login, budgeting tools)? |
| **Managing complaints** | What recurring complaints (login, OTP) should support and chatbot teams prioritize? |

---

## 2. Tasks 1–2: Data Pipeline and NLP Analysis

This phase established an end-to-end analytics pipeline from raw Play Store text to labeled sentiment and business themes.

### 2.1 Task 1: Data Collection and Preprocessing

#### Data sources

Reviews were collected from the official Google Play listings for:

| Bank | App name | Package ID |
|------|----------|------------|
| CBE | Commercial Bank of Ethiopia Mobile | `com.combanketh.mobilebanking` |
| BOA | BoA Mobile | `com.boa.boaMobileBanking` |
| Dashen | Dashen Mobile | `com.cr2.amolelight` |

**Source label:** Google Play  
**Fields captured:** review text, star rating (1–5), review date, bank identifier, source.

#### Collection methodology

- **Library:** `google-play-scraper` (Python)
- **Locale:** `lang=en`, `country=et` (Ethiopia store; English and Amharic reviews)
- **Sort order:** `NEWEST` first; `MOST_RELEVANT` used only if the per-bank quota was not met
- **Pagination:** 200 reviews per API call, ~1 s delay between requests to reduce rate-limit risk
- **Scrape target:** 650 reviews per bank (buffer above the 400 minimum to absorb duplicates)

#### Preprocessing workflow

The preprocessing module (`src/preprocessing.py`, CLI: `scripts/preprocess_reviews.py`) applies:

1. Drop rows missing review text or rating  
2. Validate ratings ∈ {1, 2, 3, 4, 5}  
3. **Deduplicate** by `review_id` when available, then by normalized review text + bank  
4. Normalize dates to `YYYY-MM-DD`  
5. Export columns: `review`, `rating`, `date`, `bank`, `source`

Outputs are written to gitignored paths: `data/raw/reviews_raw.csv` and `data/processed/reviews_clean.csv`.

#### Engineering deliverables (Task 1)

- Modular scraper and preprocessing packages under `src/`
- CLI scripts: `scrape_reviews.py`, `preprocess_reviews.py`
- `.gitignore` excluding `data/`, `*.csv`, and model caches
- GitHub Actions workflow (`.github/workflows/unittests.yml`) running `pytest` on push to `main`
- Unit tests for preprocessing (`tests/test_preprocessing.py`)
- Pull Request #1 to `main` (two commits: scaffold + scraping/preprocessing)

---

### 2.2 Task 2: Sentiment Analysis

#### Tool selection

| Approach | Role | Rationale |
|----------|------|-----------|
| **DistilBERT** (`distilbert-base-uncased-finetuned-sst-2-english`) | Primary (assignment target) | Fine-tuned on sentiment; better on informal and mixed phrasing than lexicon-only tools |
| **VADER** (`vaderSentiment`) | Comparison & fast batch runs | Lightweight, deterministic; used to produce the interim labeled dataset |

**Neutral class mapping (DistilBERT):** SST-2 is binary; confidence scores in [0.45, 0.55] are mapped to `neutral`.

**VADER thresholds (comparison):**

- **Positive:** compound ≥ 0.05  
- **Neutral:** −0.05 < compound < 0.05  
- **Negative:** compound ≤ −0.05  

Sentiment outputs per review:

- `sentiment_label` — positive / negative / neutral  
- `sentiment_score` — model confidence (DistilBERT) or |compound| (VADER)  
- `vader_compound` — raw VADER score in [−1, 1] for cross-checking  

#### Aggregation

Sentiment is aggregated by:

- **Bank** — mean confidence, % positive / negative  
- **Star rating** — mean confidence and label distribution within each 1–5 star bucket  

---

### 2.3 Task 2: Thematic Analysis

#### Keyword extraction

- **Method:** TF-IDF unigrams and bigrams (`sklearn.feature_extraction.text.TfidfVectorizer`)
- **Preprocessing:** lowercase, URL removal, English stop words
- **Output:** Top terms per bank (e.g., *app*, *good*, *transfer*, *login*)

#### Theme taxonomy

Five business-relevant themes were defined and assigned via keyword overlap (`src/themes.py`):

1. Account Access Issues  
2. Transaction Performance  
3. UI & Design  
4. Customer Support  
5. Feature Requests  

Reviews with no keyword match default to **General Feedback**.

#### Pipeline output

`scripts/run_sentiment_analysis.py` produces `data/analysis/reviews_sentiment.csv` with:

`review_id`, `review_text`, `sentiment_label`, `sentiment_score`, `identified_theme`, `bank`, `rating`, `date`, `vader_compound`

#### Engineering deliverables (Task 2)

- `src/sentiment.py`, `src/sentiment_utils.py`, `src/themes.py`
- Unit tests for sentiment helpers and theme assignment
- Pull Request #2 to `main` (two commits: NLP modules + analysis CLI/documentation)

---

## 3. Results (Current Progress Summary)

### 3.1 Data processing outcomes

| Metric | Value |
|--------|-------|
| Raw reviews scraped | **1,805** |
| Reviews after cleaning | **1,380** |
| Rows dropped (mostly duplicates) | 425 (23.5%) |
| Missing review text or rating | 0 |

**Per-bank counts (cleaned):**

| Bank | Raw scraped | Cleaned | Avg. star rating |
|------|-------------|---------|------------------|
| CBE | 650 | **466** | 3.85 |
| BOA | 650 | **517** | 3.24 |
| Dashen | 505* | **397** | 4.00 |
| **Total** | **1,805** | **1,380** | — |

\*Dashen: Play Store API returned fewer than 650 reviews (listing cap ~505). Cleaned count is 3 reviews below the 400 minimum; documented as a data-availability limitation.

The pipeline met the **≥1,200 total reviews** KPI. CBE and BOA exceeded **400 cleaned reviews per bank**; Dashen is marginally under target after deduplication.

**Duplicate drivers:** overlap between sort orders during scraping, repeated user copy-paste reviews, and identical text across pagination windows. Deduplication by `review_id` and text+bank reduced inflation.

---

### 3.2 Sentiment findings (VADER interim run)

| Bank | *n* | % Positive | % Negative | % Neutral | Mean confidence |
|------|-----|------------|------------|-----------|-----------------|
| CBE | 466 | 55.2% | 44.0% | 0.9% | 0.67 |
| BOA | 517 | 40.6% | 58.0% | 0.2% | 0.70 |
| Dashen | 397 | 58.4% | 40.1% | 0.5% | 0.70 |

**Alignment with star ratings:** For all three banks, 5-star reviews show higher positive-label rates than 1-star reviews (e.g., CBE: 70% positive labels on 5-star vs. 24% on 1-star), indicating sentiment labels are directionally consistent with user ratings.

**Bank contrast:** BOA shows the lowest average star rating (3.24) and the highest negative sentiment share (58%), consistent with its weaker Play Store position relative to CBE (3.85) and Dashen (4.00).

---

### 3.3 Thematic findings

**Theme distribution (review counts):**

| Theme | CBE | BOA | Dashen |
|-------|-----|-----|--------|
| General Feedback | 329 | 368 | 261 |
| Transaction Performance | **56** | **61** | 38 |
| UI & Design | 52 | 37 | **55** |
| Account Access Issues | 13 | **26** | 26 |
| Feature Requests | 12 | 16 | 12 |
| Customer Support | 4 | 9 | 5 |

**Scenario 1 — Slow loading / transfers (systemic check):**  
Keyword mentions of *slow*, *loading*, or *transfer* in raw review text:

| Bank | Mentions | % of bank reviews |
|------|----------|-------------------|
| CBE | 29 | 6.2% |
| BOA | 41 | 7.9% |
| Dashen | 26 | 6.5% |

**Interpretation:** Performance complaints appear across **all three apps** at similar rates (~6–8%), suggesting transfer/loading friction is a **market-wide UX concern**, not isolated to one bank. BOA shows the highest mention rate, aligning with its lower average rating.

**Scenario 2 — Feature requests:**  
Feature Requests theme is a minority bucket (12–16 reviews per bank), but TF-IDF surfaces terms such as *app*, *good*, *banking*, and *use*. Deeper n-gram mining in the final report will target explicit asks (fingerprint, budgeting, Amharic UI).

**Scenario 3 — Complaints:**  
Account Access Issues are most visible for **BOA (26)** and **Dashen (26)** vs. **CBE (13)**, indicating login/OTP/password friction may be a higher support priority for those two apps.

---

### 3.4 Top keywords (TF-IDF sample)

| Bank | Representative top terms |
|------|--------------------------|
| CBE | app, good, best, nice, cbe, bank, application |
| BOA | app, good, best, bank, boa, working, banking |
| Dashen | app, good, best, bank, nice, use, good app |

---

### 3.5 Visualization and reporting status

- **Completed:** Tabular aggregates, theme counts, keyword lists (console/CSV outputs from analysis script)  
- **Planned (Tasks 3–4):** Stakeholder charts (sentiment by bank/rating, theme bar charts, complaint trend plots) and Medium-style final narrative  

---

## 4. Discussion and Observations

### 4.1 Technical outcomes

The project established a reproducible workflow integrating:

- Google Play scraping with pagination and rate-limit handling  
- Structured preprocessing with documented drop/duplicate statistics  
- Modular NLP (sentiment + themes) with unit tests and CI  
- Version-controlled delivery via **two PRs** (Task 1 and Task 2), each with two conventional commits  

**Critical technical observations:**

- **Network and environment:** Play Store scraping requires unrestricted outbound access; sandboxed runs returned zero reviews until full network was enabled.  
- **Dashen API cap:** Not all apps expose 650+ reviews via `google-play-scraper`; limits must be documented rather than forced.  
- **DistilBERT deployment:** First-run model download (~250 MB) is slow on CPU; VADER was used for the interim labeled dataset while DistilBERT remains the primary model for final scoring (`--backend distilbert`).  
- **Language mix:** Reviews include English and Amharic; English-tuned models may underperform on Amharic text—worth noting in final recommendations.

### 4.2 Analytical observations

- **BOA underperformance** is visible in both star ratings and negative sentiment share—a coherent story for client delivery.  
- **Transaction Performance** is the leading non-general theme for CBE and BOA, supporting product investigation into transfer latency and app stability.  
- **Dashen** users comment more on **UI & Design** than transaction speed in theme counts, a different prioritization signal than CBE/BOA.  
- **Sentiment ≠ stars** for some buckets (e.g., 3-star reviews with mixed labels), reinforcing the value of text-based NLP beyond stars alone.

### 4.3 Limitations

| Limitation | Impact |
|------------|--------|
| VADER / DistilBERT not trained on Amharic banking language | May misclassify local-language reviews |
| Keyword-based themes vs. LDA/zero-shot | Themes are interpretable but may miss novel phrases |
| Same-day scrape snapshot | No longitudinal trend analysis yet |
| Dashen sample size | Slightly below 400 cleaned reviews |
| No PostgreSQL layer yet (Task 3) | Data still file-based CSV |

These limitations should be stated when presenting interim findings to bank executives.

---

## 5. Next Steps

### Task 3 — Database engineering (planned)

- Design PostgreSQL schema (banks, reviews, sentiments, themes)  
- Load cleaned and analyzed CSVs via SQLAlchemy  
- Support queryable dashboards for product teams  

### Task 4 — Insights and final report (planned)

- Publication-style report (Medium format) with bank-specific recommendations  
- Visualizations: sentiment by rating, theme comparison, complaint clusters  
- Executive summary tying scenarios 1–3 to prioritized roadmaps  

### Analytical extensions

- Run full **DistilBERT** scoring and compare agreement with VADER  
- Optional **LDA/NMF** topic modeling to refine themes  
- **Amharic-aware** sentiment or translation preprocessing  
- Time-series analysis if extended date ranges are scraped  

---

## 6. Conclusion

This interim phase delivers a working **data-to-insight pipeline** for Ethiopian fintech app reviews. Tasks 1 and 2 are complete in code, tested, and documented on GitHub (`task-1` and `task-2` pull requests).

**Demonstrated capabilities:**

- Scraping and cleaning **1,380** Play Store reviews across CBE, BOA, and Dashen  
- Sentiment labeling for **100%** of cleaned reviews (VADER interim; DistilBERT ready)  
- **Five business themes** per bank with TF-IDF keyword support  
- Early answers to Omega’s scenarios: transfer/loading issues appear **systemic**; BOA shows the weakest sentiment and rating profile; account-access themes cluster on BOA and Dashen  

Although formal visualizations and database storage remain for the final submission, the interim work provides a **rigorous, reproducible foundation** for bank-specific product recommendations in the final consultancy deliverable.

---

*Repository:* [fintech-review-analytics](https://github.com/kalkidantad/fintech-review-analytics) · PR #1 (Task 1) · PR #2 (Task 2)
