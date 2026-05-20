#!/usr/bin/env python3
"""
Build the Task 4 narrative PDF (Medium-style article with embedded figures).

Prerequisite: run `python scripts/generate_insights_visualizations.py` so PNGs exist.

Usage:
  python scripts/build_insights_report_pdf.py [--input PATH] [--figures-dir DIR] [--output PATH]
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from fpdf import FPDF

from src.config import SENTIMENT_CSV
from src.insights_metrics import (
    build_bank_insights,
    cross_bank_summary,
    recommendations_for_bank,
)


def ascii_fold(text: str) -> str:
    """FPDF core fonts are Latin-1 oriented; fold unicode for portability."""
    if not isinstance(text, str):
        text = str(text)
    norm = unicodedata.normalize("NFKD", text)
    return norm.encode("ascii", "ignore").decode("ascii")


class InsightPDF(FPDF):
    def __init__(self) -> None:
        super().__init__(format="A4")
        self.set_margins(18, 18, 18)
        self.set_auto_page_break(auto=True, margin=16)


def write_heading(pdf: InsightPDF, title: str) -> None:
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 8, ascii_fold(title))
    pdf.ln(2)


def write_subheading(pdf: InsightPDF, title: str) -> None:
    pdf.set_font("Helvetica", "B", 12)
    pdf.multi_cell(0, 7, ascii_fold(title))
    pdf.ln(1)


def write_body(pdf: InsightPDF, text: str) -> None:
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 6, ascii_fold(text))
    pdf.ln(2)


def embed_figure(pdf: InsightPDF, path: Path, width_mm: float = 175) -> None:
    if not path.exists():
        write_body(pdf, f"(Figure missing: {path.name})")
        return
    pdf.image(str(path), x=None, y=None, w=width_mm)
    pdf.ln(4)


def build_report(df: pd.DataFrame, figures_dir: Path, output: Path) -> None:
    pdf = InsightPDF()
    pdf.add_page()

    write_heading(
        pdf,
        "Fintech mobile banking reviews: insights, comparisons, and recommendations",
    )
    write_body(
        pdf,
        "This report synthesizes Google Play Store reviews for three Ethiopian retail banks "
        "(CBE, BOA, and Dashen). Sentiment labels come from DistilBERT fine-tuned on SST-2, "
        "with a neutral band on middling confidence. Themes combine keyword rules and TF-IDF "
        "terms. Figures summarize distributions; narrative sections translate patterns into "
        "prioritized product and support actions.",
    )

    write_subheading(pdf, "Ethics and data limitations")
    write_body(
        pdf,
        "Store reviews skew toward extreme experiences: users often post after failures "
        "(negativity bias) or after unusually delightful moments. The scrape is date-limited "
        "and may not represent silent satisfied users. English-centric NLP under-counts nuance "
        "in Amharic or code-switched text. Comparisons across banks are descriptive, not causal; "
        "differences in app maturity and user bases confound simple benchmarks.",
    )

    write_subheading(pdf, "Cross-bank snapshot")
    summary = cross_bank_summary(df)
    lines = [
        f"{row.bank}: n={int(row.n)}, mean rating={row.avg_rating:.2f}, "
        f"positive={row.pct_positive:.0%}, neutral={row.pct_neutral:.0%}, negative={row.pct_negative:.0%}, "
        f"dominant theme={row.top_theme}"
        for row in summary.itertuples()
    ]
    write_body(pdf, "\n".join(lines))

    embed_figure(pdf, figures_dir / "sentiment_by_bank.png")
    write_body(pdf, "Figure 1. Sentiment mix by bank (stacked percentages).")

    pdf.add_page()
    embed_figure(pdf, figures_dir / "rating_by_bank.png")
    write_body(pdf, "Figure 2. Star rating spread by bank (box plot with jittered points).")

    embed_figure(pdf, figures_dir / "themes_by_bank.png")
    write_body(pdf, "Figure 3. Theme frequency by bank (keyword-rule buckets).")

    embed_figure(pdf, figures_dir / "keywords_by_bank.png")
    write_body(pdf, "Figure 4. Top TF-IDF unigrams and bigrams by bank.")

    embed_figure(pdf, figures_dir / "sentiment_trend_time.png")
    write_body(
        pdf,
        "Figure 5. Monthly share of negative reviews when the sample spans multiple months; "
        "otherwise the script emits a placeholder note.",
    )

    for bank in sorted(df["bank"].unique()):
        pdf.add_page()
        write_heading(pdf, f"Deep dive: {bank}")
        ins = build_bank_insights(df, bank)
        write_body(
            pdf,
            f"Sample size: {ins['n']} reviews. Average rating: {ins['avg_rating']:.2f}. "
            f"Sentiment counts: {ins['sentiment_counts']}.",
        )

        write_subheading(pdf, "Satisfaction drivers (data-backed)")
        for d in ins["drivers"][:4]:
            ev = d.evidence_themes[0] if d.evidence_themes else None
            if ev:
                write_body(
                    pdf,
                    f"- {d.label}. Within the positive / high-rating slice, this theme represents "
                    f"about {ev.share_of_segment:.0%} of labeled reviews (count={ev.count}). "
                    f"Representative keywords in positive text: {', '.join(d.top_keywords[:6])}.",
                )
            else:
                write_body(pdf, f"- {d.label}.")

        write_subheading(pdf, "Pain points (data-backed)")
        for p in ins["pains"][:4]:
            ev = p.evidence_themes[0] if p.evidence_themes else None
            if ev:
                write_body(
                    pdf,
                    f"- {p.label}. Within the negative / low-rating slice, this theme represents "
                    f"about {ev.share_of_segment:.0%} of labeled reviews (count={ev.count}). "
                    f"Representative keywords in negative text: {', '.join(p.top_keywords[:6])}.",
                )
            else:
                write_body(pdf, f"- {p.label}.")

        write_subheading(pdf, "Prioritized recommendations")
        for rec in recommendations_for_bank(ins)[:3]:
            write_body(pdf, f"- {rec}")

    pdf.add_page()
    write_heading(pdf, "Closing")
    write_body(
        pdf,
        "Use these themes to sequence engineering sprints (stability and auth first), pair "
        "quantitative review mining with in-app surveys to correct for store bias, and track "
        "the same KPIs monthly after each release.",
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output))
    print(f"Wrote {output.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Task 4 PDF report")
    parser.add_argument("--input", type=Path, default=SENTIMENT_CSV)
    parser.add_argument("--figures-dir", type=Path, default=Path("reports/figures"))
    parser.add_argument("--output", type=Path, default=Path("reports/fintech_insights_report.pdf"))
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: {args.input} not found. Run sentiment analysis first.")
        sys.exit(1)

    df = pd.read_csv(args.input)
    build_report(df, args.figures_dir, args.output)


if __name__ == "__main__":
    main()
