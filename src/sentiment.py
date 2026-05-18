"""Sentiment analysis using DistilBERT (primary) and VADER (comparison/fallback)."""

from typing import TYPE_CHECKING, Literal

import pandas as pd

from src.sentiment_utils import (
    SentimentLabel,
    distilbert_label_to_sentiment,
    map_star_rating_to_sentiment,
)

if TYPE_CHECKING:
    from transformers import Pipeline

Backend = Literal["distilbert", "vader"]


def _get_sentiment_pipeline(model_name: str = "distilbert-base-uncased-finetuned-sst-2-english"):
    """Lazy-load transformers to keep imports light for unit tests."""
    from transformers import pipeline

    return pipeline(
        "sentiment-analysis",
        model=model_name,
        truncation=True,
        max_length=512,
    )


def _get_vader_analyzer():
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    return SentimentIntensityAnalyzer()


def vader_to_sentiment(compound: float) -> tuple[SentimentLabel, float]:
    """Map VADER compound score to label and confidence."""
    if compound >= 0.05:
        return "positive", min(abs(compound), 1.0)
    if compound <= -0.05:
        return "negative", min(abs(compound), 1.0)
    return "neutral", 1.0 - min(abs(compound), 1.0)


class VaderSentimentAnalyzer:
    """Lexicon-based sentiment for comparison or when DistilBERT is unavailable."""

    def __init__(self) -> None:
        self._vader = _get_vader_analyzer()

    def analyze_text(self, text: str) -> tuple[SentimentLabel, float]:
        if not text or not str(text).strip():
            return "neutral", 0.0
        compound = self._vader.polarity_scores(str(text))["compound"]
        return vader_to_sentiment(compound)

    def analyze_batch(
        self,
        texts: list[str],
        batch_size: int = 32,
    ) -> list[tuple[SentimentLabel, float]]:
        return [self.analyze_text(t) for t in texts]


class SentimentAnalyzer:
    """Transformer-based sentiment with optional VADER comparison."""

    def __init__(self, model_name: str = "distilbert-base-uncased-finetuned-sst-2-english"):
        self._pipe: Pipeline = _get_sentiment_pipeline(model_name)
        self._vader = _get_vader_analyzer()

    def analyze_text(self, text: str) -> tuple[SentimentLabel, float]:
        """Classify a single review; returns (label, confidence)."""
        if not text or not str(text).strip():
            return "neutral", 0.0

        result = self._pipe(str(text)[:512])[0]
        return distilbert_label_to_sentiment(result["label"], float(result["score"]))

    def analyze_batch(
        self,
        texts: list[str],
        batch_size: int = 32,
    ) -> list[tuple[SentimentLabel, float]]:
        """Batch sentiment classification for efficiency."""
        outputs: list[tuple[SentimentLabel, float]] = []
        for i in range(0, len(texts), batch_size):
            chunk = [str(t)[:512] if t else "" for t in texts[i : i + batch_size]]
            results = self._pipe(chunk)
            for res in results:
                outputs.append(
                    distilbert_label_to_sentiment(res["label"], float(res["score"]))
                )
        return outputs

    def vader_score(self, text: str) -> float:
        """Return compound VADER score in [-1, 1] for comparison."""
        if not text:
            return 0.0
        return self._vader.polarity_scores(str(text))["compound"]


def add_sentiment_columns(
    df: pd.DataFrame,
    text_col: str = "review",
    rating_col: str = "rating",
    batch_size: int = 32,
    backend: Backend = "distilbert",
) -> pd.DataFrame:
    """
    Add sentiment_label and sentiment_score columns to a reviews DataFrame.

    Uses DistilBERT SST-2 by default; pass backend='vader' for lexicon-only runs.
    """
    texts = df[text_col].fillna("").tolist()
    vader = VaderSentimentAnalyzer()

    if backend == "vader":
        analyzer: SentimentAnalyzer | VaderSentimentAnalyzer = vader
    else:
        analyzer = SentimentAnalyzer()

    labels_scores = analyzer.analyze_batch(texts, batch_size=batch_size)

    out = df.copy()
    out["sentiment_label"] = [ls[0] for ls in labels_scores]
    out["sentiment_score"] = [ls[1] for ls in labels_scores]
    out["vader_compound"] = [
        vader._vader.polarity_scores(str(t))["compound"] if t else 0.0 for t in texts
    ]

    mask_empty = out[text_col].isna() | (out[text_col].str.strip() == "")
    if mask_empty.any() and rating_col in out.columns:
        out.loc[mask_empty, "sentiment_label"] = out.loc[mask_empty, rating_col].apply(
            map_star_rating_to_sentiment
        )

    return out


def aggregate_sentiment_by_bank(df: pd.DataFrame) -> pd.DataFrame:
    """Mean sentiment score and label distribution per bank."""
    label_map = {"positive": 1, "neutral": 0, "negative": -1}
    working = df.copy()
    working["_sent_num"] = working["sentiment_label"].map(label_map)

    return (
        working.groupby("bank")
        .agg(
            review_count=("sentiment_score", "count"),
            mean_confidence=("sentiment_score", "mean"),
            mean_sentiment_numeric=("_sent_num", "mean"),
            pct_positive=("sentiment_label", lambda s: (s == "positive").mean() * 100),
            pct_negative=("sentiment_label", lambda s: (s == "negative").mean() * 100),
        )
        .reset_index()
    )


def aggregate_sentiment_by_rating(df: pd.DataFrame) -> pd.DataFrame:
    """Mean sentiment confidence grouped by star rating."""
    return (
        df.groupby(["bank", "rating"])
        .agg(
            count=("sentiment_score", "count"),
            mean_confidence=("sentiment_score", "mean"),
            pct_positive_label=(
                "sentiment_label",
                lambda s: (s == "positive").mean() * 100,
            ),
        )
        .reset_index()
    )
