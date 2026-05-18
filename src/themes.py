"""Thematic analysis: TF-IDF keywords, n-grams, and business theme mapping."""

import re
from collections import defaultdict
from typing import Any

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

# Business-relevant themes with keyword triggers (grouping logic)
THEME_KEYWORDS: dict[str, list[str]] = {
    "Account Access Issues": [
        "login", "log in", "sign in", "password", "pin", "otp", "verification",
        "locked", "block", "access", "register", "account open", "biometric",
        "fingerprint", "face id",
    ],
    "Transaction Performance": [
        "slow", "loading", "transfer", "transaction", "delay", "pending",
        "timeout", "crash", "freeze", "hang", "stuck", "failed", "error",
        "payment", "send money", "withdraw",
    ],
    "UI & Design": [
        "ui", "interface", "design", "layout", "easy", "simple", "navigate",
        "user friendly", "look", "screen", "update", "version",
    ],
    "Customer Support": [
        "support", "customer service", "call", "branch", "help", "response",
        "complaint", "resolve", "contact", "agent",
    ],
    "Feature Requests": [
        "feature", "add", "need", "want", "wish", "budget", "loan", "saving",
        "notification", "alert", "dark mode", "language", "amharic",
        "fingerprint", "qr", "bill pay", "airtime",
    ],
}


def preprocess_text_for_tfidf(text: str) -> str:
    """Lowercase, remove URLs and excess whitespace."""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"http\S+|www\.\S+", "", text)
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_top_keywords(
    texts: list[str],
    n_keywords: int = 20,
    ngram_range: tuple[int, int] = (1, 2),
    min_df: int = 2,
) -> list[tuple[str, float]]:
    """Extract top TF-IDF terms from a corpus of review texts."""
    cleaned = [preprocess_text_for_tfidf(t) for t in texts]
    cleaned = [t for t in cleaned if t]
    if len(cleaned) < 2:
        return []

    vectorizer = TfidfVectorizer(
        ngram_range=ngram_range,
        min_df=min_df,
        max_df=0.85,
        stop_words="english",
        max_features=500,
    )
    try:
        matrix = vectorizer.fit_transform(cleaned)
    except ValueError:
        return []

    scores = matrix.sum(axis=0).A1
    terms = vectorizer.get_feature_names_out()
    ranked = sorted(zip(terms, scores), key=lambda x: x[1], reverse=True)
    return ranked[:n_keywords]


def assign_theme(text: str) -> str:
    """
    Map a review to the best-matching business theme via keyword overlap.

    Returns the theme with the most keyword hits; defaults to 'General Feedback'.
    """
    normalized = preprocess_text_for_tfidf(text)
    if not normalized:
        return "General Feedback"

    best_theme = "General Feedback"
    best_score = 0

    for theme, keywords in THEME_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in normalized)
        if score > best_score:
            best_score = score
            best_theme = theme

    return best_theme


def assign_themes_batch(texts: list[str]) -> list[str]:
    """Assign a theme to each review in a batch."""
    return [assign_theme(t) for t in texts]


def extract_themes_per_bank(
    df: pd.DataFrame,
    text_col: str = "review",
    bank_col: str = "bank",
) -> dict[str, dict[str, Any]]:
    """
    For each bank, extract top keywords and theme distribution.

    Returns nested dict: bank -> {keywords, theme_counts, top_examples}.
    """
    results: dict[str, dict[str, Any]] = {}

    for bank in df[bank_col].unique():
        subset = df[df[bank_col] == bank]
        texts = subset[text_col].tolist()
        keywords = extract_top_keywords(texts)
        themes = assign_themes_batch(texts)

        theme_counts: dict[str, int] = defaultdict(int)
        for t in themes:
            theme_counts[t] += 1

        results[bank] = {
            "review_count": len(subset),
            "top_keywords": keywords[:15],
            "theme_distribution": dict(theme_counts),
        }

    return results


def add_theme_column(df: pd.DataFrame, text_col: str = "review") -> pd.DataFrame:
    """Add identified_theme column based on keyword-based theme mapping."""
    out = df.copy()
    out["identified_theme"] = assign_themes_batch(out[text_col].fillna("").tolist())
    return out
