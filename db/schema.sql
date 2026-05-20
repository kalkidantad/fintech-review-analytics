-- bank_reviews database schema (Task 3)
-- Apply: psql -U postgres -d bank_reviews -f db/schema.sql

BEGIN;

CREATE TABLE IF NOT EXISTS banks (
    bank_id INTEGER PRIMARY KEY,
    bank_name VARCHAR(255) NOT NULL,
    app_name VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id INTEGER PRIMARY KEY,
    bank_id INTEGER NOT NULL REFERENCES banks (bank_id) ON DELETE CASCADE,
    review_text TEXT NOT NULL,
    rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review_date DATE,
    sentiment_label VARCHAR(20),
    sentiment_score DOUBLE PRECISION,
    identified_theme VARCHAR(128),
    source VARCHAR(64) NOT NULL DEFAULT 'Google Play'
);

CREATE INDEX IF NOT EXISTS idx_reviews_bank_id ON reviews (bank_id);
CREATE INDEX IF NOT EXISTS idx_reviews_review_date ON reviews (review_date);
CREATE INDEX IF NOT EXISTS idx_reviews_sentiment_label ON reviews (sentiment_label);

COMMIT;
