"""Tests for thematic analysis and keyword extraction."""

from src.themes import assign_theme, preprocess_text_for_tfidf, extract_top_keywords


def test_preprocess_text_removes_urls():
    text = "Check https://example.com for help"
    result = preprocess_text_for_tfidf(text)
    assert "https" not in result
    assert "example" not in result or "help" in result


def test_assign_theme_login():
    assert assign_theme("Cannot login, OTP not received") == "Account Access Issues"


def test_assign_theme_slow_transfer():
    assert assign_theme("Transfer is very slow and app keeps loading") == "Transaction Performance"


def test_assign_theme_feature_request():
    assert assign_theme("Please add fingerprint login and budgeting tools") == "Feature Requests"


def test_extract_top_keywords_minimum_corpus():
    texts = ["slow transfer"] * 5 + ["fast and easy ui"] * 5
    keywords = extract_top_keywords(texts, min_df=2)
    assert len(keywords) > 0
    terms = [k[0] for k in keywords]
    assert any("slow" in t or "transfer" in t or "fast" in t for t in terms)


def test_assign_theme_general_fallback():
    assert assign_theme("ok") == "General Feedback"
