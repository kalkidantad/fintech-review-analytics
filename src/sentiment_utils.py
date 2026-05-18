"""Pure sentiment helper functions (no ML model dependencies)."""

from typing import Literal

SentimentLabel = Literal["positive", "negative", "neutral"]


def map_star_rating_to_sentiment(rating: int) -> SentimentLabel:
    """Fallback heuristic when transformer confidence is low."""
    if rating >= 4:
        return "positive"
    if rating <= 2:
        return "negative"
    return "neutral"


def distilbert_label_to_sentiment(label: str, score: float) -> tuple[SentimentLabel, float]:
    """
    Map SST-2 labels (POSITIVE/NEGATIVE) to three-class sentiment.

    Scores near 0.5 are treated as neutral.
    """
    label_upper = label.upper()
    if 0.45 <= score <= 0.55:
        return "neutral", score
    if "POS" in label_upper:
        return "positive", score
    return "negative", score
