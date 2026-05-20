#!/usr/bin/env python3
"""
Load cleaned or analyzed review CSV into PostgreSQL (Task 3).

Expects database `bank_reviews` and tables from db/schema.sql.

Environment variables (defaults in parentheses):
  PGHOST (localhost), PGPORT (5432), PGDATABASE (bank_reviews),
  PGUSER (postgres), PGPASSWORD (empty)

Usage:
  # After running sentiment pipeline (recommended — full columns):
  python scripts/load_reviews_to_postgres.py --input data/analysis/reviews_sentiment.csv

  # Clean CSV only (sentiment/theme columns stored as NULL):
  python scripts/load_reviews_to_postgres.py --input data/processed/reviews_clean.csv --from-clean

  # Apply schema then load:
  python scripts/load_reviews_to_postgres.py --schema db/schema.sql
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

try:
    import psycopg2
    from psycopg2.extras import execute_batch
except ImportError as e:  # pragma: no cover
    raise SystemExit("Install psycopg2: pip install psycopg2-binary") from e

from src.config import BANK_APPS, CLEAN_REVIEWS_CSV, SENTIMENT_CSV, SOURCE_LABEL


def bank_key_to_id() -> dict[str, int]:
    """Stable integer PKs for banks (must match seed rows)."""
    keys = list(BANK_APPS.keys())
    return {k: i + 1 for i, k in enumerate(keys)}


def connect():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "bank_reviews"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", ""),
    )


def apply_schema(conn, schema_path: Path) -> None:
    with schema_path.open() as f:
        sql_text = f.read()
    with conn.cursor() as cur:
        cur.execute(sql_text)
    conn.commit()


def seed_banks(conn) -> None:
    key_to_id = bank_key_to_id()
    rows = []
    for key, meta in BANK_APPS.items():
        # Human-readable institution name for reporting
        full_name = {
            "CBE": "Commercial Bank of Ethiopia",
            "BOA": "Bank of Abyssinia",
            "Dashen": "Dashen Bank",
        }.get(key, meta["bank_label"])
        rows.append((key_to_id[key], full_name, meta["app_name"]))
    with conn.cursor() as cur:
        execute_batch(
            cur,
            """
            INSERT INTO banks (bank_id, bank_name, app_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (bank_id) DO UPDATE
            SET bank_name = EXCLUDED.bank_name,
                app_name = EXCLUDED.app_name
            """,
            rows,
        )
    conn.commit()


def load_dataframe(
    path: Path,
    from_clean: bool,
) -> pd.DataFrame:
    df = pd.read_csv(path)
    if from_clean:
        required = {"review", "rating", "date", "bank", "source"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Clean CSV missing columns: {sorted(missing)}")
        df = df.copy()
        df["review_id"] = range(1, len(df) + 1)
        df["review_text"] = df["review"]
        df["sentiment_label"] = None
        df["sentiment_score"] = None
        df["identified_theme"] = None
    else:
        need = {"review_id", "review_text", "bank", "rating", "date"}
        missing = need - set(df.columns)
        if missing:
            raise ValueError(f"Analysis CSV missing columns: {sorted(missing)}")
        df = df.copy()
        if "identified_theme" not in df.columns:
            df["identified_theme"] = None
        if "sentiment_label" not in df.columns:
            df["sentiment_label"] = None
        if "sentiment_score" not in df.columns:
            df["sentiment_score"] = None

    if "source" not in df.columns:
        df["source"] = SOURCE_LABEL

    df["rating"] = pd.to_numeric(df["rating"], errors="coerce").astype("Int64")
    bad = df["rating"].isna() | ~df["rating"].between(1, 5)
    if bad.any():
        df = df[~bad].copy()

    key_to_id = bank_key_to_id()
    unknown = ~df["bank"].isin(key_to_id)
    if unknown.any():
        bad_banks = sorted(df.loc[unknown, "bank"].unique().tolist())
        raise ValueError(f"Unknown bank labels in CSV: {bad_banks}")
    df["bank_id"] = df["bank"].map(key_to_id)

    # Parse dates; allow NULL review_date if unparseable
    parsed = pd.to_datetime(df["date"], errors="coerce", utc=True)
    df["review_date"] = parsed.dt.date

    return df


def replace_reviews(conn, df: pd.DataFrame) -> int:
    cols = [
        "review_id",
        "bank_id",
        "review_text",
        "rating",
        "review_date",
        "sentiment_label",
        "sentiment_score",
        "identified_theme",
        "source",
    ]
    payload = df[cols].copy()
    payload["sentiment_score"] = pd.to_numeric(payload["sentiment_score"], errors="coerce")

    rows: list[tuple] = []
    for _, r in payload.iterrows():
        rows.append(
            (
                int(r["review_id"]),
                int(r["bank_id"]),
                str(r["review_text"]),
                int(r["rating"]),
                r["review_date"],
                None if pd.isna(r["sentiment_label"]) else str(r["sentiment_label"]),
                None if pd.isna(r["sentiment_score"]) else float(r["sentiment_score"]),
                None if pd.isna(r["identified_theme"]) else str(r["identified_theme"]),
                str(r["source"]),
            )
        )

    with conn.cursor() as cur:
        cur.execute("DELETE FROM reviews;")
        execute_batch(
            cur,
            """
            INSERT INTO reviews (
                review_id, bank_id, review_text, rating, review_date,
                sentiment_label, sentiment_score, identified_theme, source
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """,
            rows,
            page_size=500,
        )
    conn.commit()
    return len(rows)


def run_verification_queries(conn) -> None:
    queries = [
        ("Total reviews", "SELECT COUNT(*) FROM reviews"),
        (
            "Reviews per bank",
            """
            SELECT b.bank_name, COUNT(r.review_id) AS review_count
            FROM banks b
            LEFT JOIN reviews r ON r.bank_id = b.bank_id
            GROUP BY b.bank_id, b.bank_name
            ORDER BY b.bank_id
            """,
        ),
        (
            "Average rating per bank",
            """
            SELECT b.bank_name, ROUND(AVG(r.rating)::numeric, 3) AS avg_rating
            FROM banks b
            LEFT JOIN reviews r ON r.bank_id = b.bank_id
            GROUP BY b.bank_id, b.bank_name
            ORDER BY b.bank_id
            """,
        ),
        (
            "Nulls in key columns",
            """
            SELECT
                COUNT(*) FILTER (WHERE review_text IS NULL OR btrim(review_text) = '') AS empty_review_text,
                COUNT(*) FILTER (WHERE rating IS NULL) AS null_rating,
                COUNT(*) FILTER (WHERE review_date IS NULL) AS null_review_date,
                COUNT(*) FILTER (WHERE sentiment_label IS NULL) AS null_sentiment,
                COUNT(*) FILTER (WHERE identified_theme IS NULL OR btrim(identified_theme) = '') AS empty_theme,
                COUNT(*) FILTER (WHERE source IS NULL OR btrim(source) = '') AS empty_source
            FROM reviews
            """,
        ),
    ]
    with conn.cursor() as cur:
        for title, q in queries:
            print(f"\n--- {title} ---")
            cur.execute(q)
            rows = cur.fetchall()
            colnames = [d[0] for d in cur.description]
            print(", ".join(colnames))
            for row in rows:
                print(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="Load review CSV into PostgreSQL")
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Path to reviews_sentiment.csv or reviews_clean.csv",
    )
    parser.add_argument(
        "--from-clean",
        action="store_true",
        help="Treat input as cleaned CSV (no sentiment columns).",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=None,
        help="If set, run this SQL file before loading (creates tables).",
    )
    parser.add_argument("--verify-only", action="store_true", help="Only print verification queries.")
    args = parser.parse_args()

    inp = args.input
    if not args.verify_only:
        if inp is None:
            inp = CLEAN_REVIEWS_CSV if args.from_clean else SENTIMENT_CSV
        if not inp.exists():
            print(f"Error: input not found: {inp}")
            print("Run preprocessing / sentiment scripts first, or pass --input.")
            sys.exit(1)

    conn = connect()
    try:
        if args.schema:
            apply_schema(conn, args.schema)
            print(f"Applied schema from {args.schema}")

        seed_banks(conn)
        print("Seeded banks table.")

        if args.verify_only:
            run_verification_queries(conn)
            return

        df = load_dataframe(inp, from_clean=args.from_clean)
        n = replace_reviews(conn, df)
        print(f"Inserted {n} reviews from {inp}")

        run_verification_queries(conn)

        if n < 400:
            print(
                f"\nWarning: fewer than 400 rows loaded ({n}). "
                "Scrape and preprocess to meet the assignment KPI."
            )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
