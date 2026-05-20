"""Aggregations and evidence helpers for Task 4 insights and reporting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.themes import extract_top_keywords


@dataclass
class ThemeEvidence:
    theme: str
    share_of_segment: float
    count: int


@dataclass
class DriverOrPain:
    label: str
    kind: str  # "driver" | "pain"
    evidence_themes: list[ThemeEvidence]
    top_keywords: list[str]


def _sentiment_positive(s: str) -> bool:
    return str(s).lower() == "positive"


def _sentiment_negative(s: str) -> bool:
    return str(s).lower() == "negative"


def segment_theme_shares(df: pd.DataFrame, mask: pd.Series, top_n: int = 3) -> list[ThemeEvidence]:
    seg = df.loc[mask & df["identified_theme"].notna() & (df["identified_theme"].str.strip() != "")]
    if seg.empty:
        return []
    counts = seg["identified_theme"].value_counts()
    total = int(counts.sum())
    out: list[ThemeEvidence] = []
    for theme, c in counts.head(top_n).items():
        out.append(ThemeEvidence(theme=str(theme), share_of_segment=c / total if total else 0.0, count=int(c)))
    return out


def top_keywords_for_mask(df: pd.DataFrame, mask: pd.Series, k: int = 8) -> list[str]:
    texts = df.loc[mask, "review_text"].dropna().astype(str).tolist()
    ranked = extract_top_keywords(texts, n_keywords=k, min_df=2)
    return [t for t, _ in ranked[:k]]


def build_bank_insights(df: pd.DataFrame, bank: str) -> dict[str, Any]:
    """Structured drivers, pain points, and keyword evidence for one bank."""
    b = df[df["bank"] == bank].copy()
    if b.empty:
        return {"bank": bank, "n": 0, "drivers": [], "pains": []}

    pos = b["sentiment_label"].map(_sentiment_positive)
    neg = b["sentiment_label"].map(_sentiment_negative)
    high = b["rating"] >= 4
    low = b["rating"] <= 2

    driver_mask = pos | high
    pain_mask = neg | low

    driver_themes = segment_theme_shares(b, driver_mask, top_n=4)
    pain_themes = segment_theme_shares(b, pain_mask, top_n=4)

    pos_kw = top_keywords_for_mask(b, pos, k=10)
    neg_kw = top_keywords_for_mask(b, neg, k=10)

    drivers: list[DriverOrPain] = []
    for ev in driver_themes[:2]:
        label = f"{ev.theme} (visible in satisfied / high-rating segment)"
        drivers.append(
            DriverOrPain(
                label=label,
                kind="driver",
                evidence_themes=[ev],
                top_keywords=pos_kw[:6],
            )
        )
    # Ensure at least two drivers from themes; if themes thin, add rating-based narrative
    if len(drivers) < 2 and len(driver_themes) > 0:
        for ev in driver_themes[2:4]:
            if len(drivers) >= 2:
                break
            drivers.append(
                DriverOrPain(
                    label=f"{ev.theme} (recurring among positive / 4–5★ reviews)",
                    kind="driver",
                    evidence_themes=[ev],
                    top_keywords=pos_kw[:6],
                )
            )

    pains: list[DriverOrPain] = []
    for ev in pain_themes[:2]:
        pains.append(
            DriverOrPain(
                label=f"{ev.theme} (concentrated in negative / low-rating segment)",
                kind="pain",
                evidence_themes=[ev],
                top_keywords=neg_kw[:6],
            )
        )
    if len(pains) < 2 and len(pain_themes) > 2:
        for ev in pain_themes[2:4]:
            if len(pains) >= 2:
                break
            pains.append(
                DriverOrPain(
                    label=f"{ev.theme} (emerging complaint theme)",
                    kind="pain",
                    evidence_themes=[ev],
                    top_keywords=neg_kw[:6],
                )
            )

    used_driver_themes = {d.evidence_themes[0].theme for d in drivers if d.evidence_themes}
    if len(drivers) < 2:
        for ev in segment_theme_shares(b, high, top_n=5):
            if len(drivers) >= 2:
                break
            if ev.theme in used_driver_themes:
                continue
            drivers.append(
                DriverOrPain(
                    label=f"{ev.theme} (strong among 4-5 star reviews)",
                    kind="driver",
                    evidence_themes=[ev],
                    top_keywords=pos_kw[:6],
                )
            )

    used_pain_themes = {p.evidence_themes[0].theme for p in pains if p.evidence_themes}
    if len(pains) < 2:
        for ev in segment_theme_shares(b, low, top_n=5):
            if len(pains) >= 2:
                break
            if ev.theme in used_pain_themes:
                continue
            pains.append(
                DriverOrPain(
                    label=f"{ev.theme} (concentrated among 1-2 star reviews)",
                    kind="pain",
                    evidence_themes=[ev],
                    top_keywords=neg_kw[:6],
                )
            )

    return {
        "bank": bank,
        "n": len(b),
        "avg_rating": float(b["rating"].mean()) if len(b) else 0.0,
        "sentiment_counts": b["sentiment_label"].value_counts(dropna=False).to_dict(),
        "drivers": drivers,
        "pains": pains,
        "keywords_positive_segment": pos_kw,
        "keywords_negative_segment": neg_kw,
    }


def recommendations_for_bank(insights: dict[str, Any]) -> list[str]:
    """Two concrete product/support recommendations grounded in pain themes."""
    recs: list[str] = []
    pains: list[DriverOrPain] = insights.get("pains", [])
    for p in pains[:2]:
        if not p.evidence_themes:
            continue
        th = p.evidence_themes[0]
        kw_hint = ", ".join(p.top_keywords[:4]) if p.top_keywords else "review language"
        recs.append(
            f"Address {th.theme}: it accounts for ~{th.share_of_segment:.0%} of low-rating / negative "
            f"reviews for this bank (n={th.count}). Prioritize UX and telemetry around: {kw_hint}."
        )
    if len(recs) < 2:
        recs.append(
            "Instrument key flows (login, transfer, OTP) with funnel analytics and staged rollouts "
            "so regressions are caught before they dominate store reviews."
        )
    return recs[:4]


def cross_bank_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for bank, g in df.groupby("bank"):
        vc_sent = g["sentiment_label"].value_counts(normalize=True)
        th = g["identified_theme"].dropna()
        top_theme = None
        if not th.empty:
            top_theme = str(th.value_counts().idxmax())
        rows.append(
            {
                "bank": bank,
                "n": len(g),
                "avg_rating": g["rating"].mean(),
                "pct_positive": float(vc_sent.get("positive", 0.0)),
                "pct_neutral": float(vc_sent.get("neutral", 0.0)),
                "pct_negative": float(vc_sent.get("negative", 0.0)),
                "top_theme": top_theme,
            }
        )
    return pd.DataFrame(rows).sort_values("bank")
