"""Tests for sentiment helper logic (no transformer model load)."""

from src.sentiment import vader_to_sentiment
from src.sentiment_utils import distilbert_label_to_sentiment, map_star_rating_to_sentiment


def test_map_star_rating_positive():
    assert map_star_rating_to_sentiment(5) == "positive"
    assert map_star_rating_to_sentiment(4) == "positive"


def test_map_star_rating_negative():
    assert map_star_rating_to_sentiment(1) == "negative"
    assert map_star_rating_to_sentiment(2) == "negative"


def test_map_star_rating_neutral():
    assert map_star_rating_to_sentiment(3) == "neutral"


def test_distilbert_positive_label():
    label, score = distilbert_label_to_sentiment("POSITIVE", 0.92)
    assert label == "positive"
    assert score == 0.92


def test_distilbert_negative_label():
    label, _ = distilbert_label_to_sentiment("NEGATIVE", 0.88)
    assert label == "negative"


def test_distilbert_neutral_band():
    label, _ = distilbert_label_to_sentiment("POSITIVE", 0.50)
    assert label == "neutral"


def test_vader_positive():
    label, _ = vader_to_sentiment(0.8)
    assert label == "positive"


def test_vader_negative():
    label, _ = vader_to_sentiment(-0.6)
    assert label == "negative"


def test_vader_neutral():
    label, _ = vader_to_sentiment(0.01)
    assert label == "neutral"
