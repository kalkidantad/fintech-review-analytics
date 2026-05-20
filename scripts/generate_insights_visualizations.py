#!/usr/bin/env python3
"""
Generate Task 4 visualizations from reviews_sentiment.csv.

Writes PNG figures under reports/figures/ (default).

Usage:
  python scripts/generate_insights_visualizations.py [--input PATH] [--output-dir DIR]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from src.config import SENTIMENT_CSV
from src.themes import extract_top_keywords


def sentiment_stacked_by_bank(df: pd.DataFrame, out: Path) -> None:
    order = sorted(df["bank"].unique())
    ct = pd.crosstab(df["bank"], df["sentiment_label"])
    ct = ct.reindex(order)
    ct_pct = ct.div(ct.sum(axis=1), axis=0) * 100
    ax = ct_pct.plot(kind="bar", stacked=True, figsize=(9, 5), colormap="viridis")
    plt.title("Sentiment distribution by bank (% of reviews)")
    plt.ylabel("Percent")
    plt.xlabel("Bank")
    plt.legend(title="Sentiment", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(out, dpi=160)
    plt.close()


def rating_distribution_by_bank(df: pd.DataFrame, out: Path) -> None:
    plt.figure(figsize=(9, 5))
    sns.boxplot(data=df, x="bank", y="rating", order=sorted(df["bank"].unique()))
    sns.stripplot(
        data=df,
        x="bank",
        y="rating",
        order=sorted(df["bank"].unique()),
        color="black",
        alpha=0.12,
        size=2,
    )
    plt.title("Star rating distribution per bank")
    plt.xlabel("Bank")
    plt.ylabel("Rating (1–5)")
    plt.tight_layout()
    plt.savefig(out, dpi=160)
    plt.close()


def theme_frequency_by_bank(df: pd.DataFrame, out: Path) -> None:
    sub = df[df["identified_theme"].notna() & (df["identified_theme"].str.strip() != "")]
    if sub.empty:
        plt.figure(figsize=(8, 4))
        plt.text(0.1, 0.5, "No theme data to plot.")
        plt.axis("off")
        plt.savefig(out, dpi=120)
        plt.close()
        return
    banks = sorted(sub["bank"].unique())
    fig, axes = plt.subplots(1, len(banks), figsize=(5 * len(banks), 5), squeeze=False)
    for ax, bank in zip(axes[0], banks):
        counts = sub.loc[sub["bank"] == bank, "identified_theme"].value_counts().head(8)
        counts.sort_values().plot(kind="barh", ax=ax, color="steelblue")
        ax.set_title(f"Top themes — {bank}")
        ax.set_xlabel("Review count")
    plt.tight_layout()
    plt.savefig(out, dpi=160)
    plt.close()


def keyword_frequency_by_bank(df: pd.DataFrame, out: Path) -> None:
    banks = sorted(df["bank"].unique())
    fig, axes = plt.subplots(1, len(banks), figsize=(5 * len(banks), 5), squeeze=False)
    for ax, bank in zip(axes[0], banks):
        texts = df.loc[df["bank"] == bank, "review_text"].dropna().astype(str).tolist()
        top = extract_top_keywords(texts, n_keywords=12, min_df=2)
        if not top:
            ax.text(0.1, 0.5, "Insufficient corpus for TF-IDF")
            ax.axis("off")
            continue
        terms = [t for t, _ in top][::-1]
        scores = [s for _, s in top][::-1]
        ax.barh(terms, scores, color="darkorange")
        ax.set_title(f"Top TF-IDF terms — {bank}")
        ax.set_xlabel("Aggregate TF-IDF score")
    plt.tight_layout()
    plt.savefig(out, dpi=160)
    plt.close()


def sentiment_trend_over_time(df: pd.DataFrame, out: Path) -> None:
    d = df.copy()
    d["review_date"] = pd.to_datetime(d["date"], errors="coerce", utc=True)
    d = d.dropna(subset=["review_date"])
    if d.empty or d["review_date"].dt.to_period("M").nunique() < 2:
        plt.figure(figsize=(8, 4))
        plt.text(
            0.05,
            0.55,
            "Date span is too narrow for a meaningful monthly trend plot.",
            fontsize=11,
        )
        plt.axis("off")
        plt.savefig(out, dpi=120)
        plt.close()
        return
    plt.figure(figsize=(10, 5))
    for bank in sorted(d["bank"].unique()):
        sub = d[d["bank"] == bank]
        month = sub["review_date"].dt.to_period("M")
        neg = sub["sentiment_label"].astype(str).str.lower() == "negative"
        share = (
            pd.DataFrame({"month": month, "neg": neg}).groupby("month", sort=True)["neg"].mean()
        )
        share.index = share.index.to_timestamp()
        share.plot(label=bank)
    plt.title("Share of negative reviews by month")
    plt.ylabel("Fraction negative")
    plt.xlabel("Month")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out, dpi=160)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate insight plots for Task 4")
    parser.add_argument("--input", type=Path, default=SENTIMENT_CSV)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/figures"))
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: {args.input} not found. Run sentiment analysis first.")
        sys.exit(1)

    df = pd.read_csv(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    sentiment_stacked_by_bank(df, args.output_dir / "sentiment_by_bank.png")
    rating_distribution_by_bank(df, args.output_dir / "rating_by_bank.png")
    theme_frequency_by_bank(df, args.output_dir / "themes_by_bank.png")
    keyword_frequency_by_bank(df, args.output_dir / "keywords_by_bank.png")
    sentiment_trend_over_time(df, args.output_dir / "sentiment_trend_time.png")

    print(f"Saved figures to {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
