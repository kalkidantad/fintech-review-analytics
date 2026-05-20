-- Data integrity checks for bank_reviews (run after load)
-- psql -U postgres -d bank_reviews -f db/verify_queries.sql

\echo '--- Total reviews ---'
SELECT COUNT(*) AS total_reviews FROM reviews;

\echo '--- Reviews per bank ---'
SELECT b.bank_name, COUNT(r.review_id) AS review_count
FROM banks b
LEFT JOIN reviews r ON r.bank_id = b.bank_id
GROUP BY b.bank_id, b.bank_name
ORDER BY b.bank_id;

\echo '--- Average rating per bank ---'
SELECT b.bank_name, ROUND(AVG(r.rating)::numeric, 3) AS avg_rating
FROM banks b
LEFT JOIN reviews r ON r.bank_id = b.bank_id
GROUP BY b.bank_id, b.bank_name
ORDER BY b.bank_id;

\echo '--- Null counts in key review columns ---'
SELECT
    COUNT(*) FILTER (WHERE review_text IS NULL OR btrim(review_text) = '') AS null_or_empty_review_text,
    COUNT(*) FILTER (WHERE rating IS NULL) AS null_rating,
    COUNT(*) FILTER (WHERE review_date IS NULL) AS null_review_date,
    COUNT(*) FILTER (WHERE sentiment_label IS NULL) AS null_sentiment_label,
    COUNT(*) FILTER (WHERE identified_theme IS NULL OR btrim(identified_theme) = '') AS null_or_empty_theme,
    COUNT(*) FILTER (WHERE source IS NULL OR btrim(source) = '') AS null_or_empty_source
FROM reviews;
