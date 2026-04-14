-- =====================================================
-- שאילתות SQL מוכנות לדשבורד Databricks
-- שם הטבלה: claims_2025 (או לפי השם שבחרת)
-- =====================================================


-- ===== 1. סטטיסטיקות כלליות (KPI) =====
SELECT
    COUNT(*) AS total_claims,
    SUM(amount_claimed) AS total_claimed,
    SUM(amount_paid) AS total_paid,
    COUNT(DISTINCT insured_id) AS unique_insured,
    COUNT(DISTINCT provider) AS unique_providers,
    ROUND(AVG(amount_claimed), 0) AS avg_amount
FROM claims_2025;


-- ===== 2. Top 20 מבוטחים לפי תדירות (טבלה + בר) =====
SELECT
    insured_name,
    insured_id,
    COUNT(*) AS claims_count,
    SUM(amount_claimed) AS total_amount,
    COUNT(DISTINCT provider) AS providers_used
FROM claims_2025
GROUP BY insured_name, insured_id
ORDER BY claims_count DESC
LIMIT 20;


-- ===== 3. נותני שירות מובילים (בר / פאי) =====
SELECT
    provider,
    COUNT(*) AS claims,
    ROUND(AVG(amount_claimed), 0) AS avg_amount,
    COUNT(DISTINCT insured_id) AS unique_insured
FROM claims_2025
GROUP BY provider
ORDER BY claims DESC
LIMIT 15;


-- ===== 4. התפלגות לפי כיסוי (פאי) =====
SELECT
    coverage,
    COUNT(*) AS claims,
    SUM(amount_claimed) AS total_amount
FROM claims_2025
GROUP BY coverage
ORDER BY claims DESC;


-- ===== 5. התפלגות חודשית (קו / בר) =====
SELECT
    MONTH(date) AS month_num,
    DATE_FORMAT(date, 'yyyy-MM') AS month,
    COUNT(*) AS claims,
    SUM(amount_claimed) AS total_amount
FROM claims_2025
GROUP BY MONTH(date), DATE_FORMAT(date, 'yyyy-MM')
ORDER BY month_num;


-- ===== 6. ריכוזי מעסיקים חשודים (טבלה) =====
WITH emp_counts AS (
    SELECT
        provider,
        employer,
        COUNT(*) AS count
    FROM claims_2025
    GROUP BY provider, employer
),
prov_totals AS (
    SELECT
        provider,
        COUNT(*) AS total
    FROM claims_2025
    GROUP BY provider
)
SELECT
    e.provider,
    e.employer,
    e.count,
    p.total,
    ROUND(e.count * 100.0 / p.total, 1) AS pct_of_provider
FROM emp_counts e
JOIN prov_totals p ON e.provider = p.provider
WHERE e.count * 100.0 / p.total > 30
  AND p.total > 20
ORDER BY pct_of_provider DESC;


-- ===== 7. תביעות מפוליסה חדשה (60 יום) =====
SELECT
    insured_name,
    insured_id,
    policy_start,
    date AS claim_date,
    DATEDIFF(date, policy_start) AS days_since_start,
    coverage,
    amount_claimed
FROM claims_2025
WHERE DATEDIFF(date, policy_start) BETWEEN 0 AND 60
ORDER BY days_since_start;


-- ===== 8. סכומים עגולים חשודים =====
SELECT
    provider,
    COUNT(*) AS round_amount_claims,
    SUM(amount_claimed) AS total
FROM claims_2025
WHERE amount_claimed % 500 = 0 AND amount_claimed >= 500
GROUP BY provider
ORDER BY round_amount_claims DESC;


-- ===== 9. אשכולות משפחתיים =====
WITH family_data AS (
    SELECT
        ELEMENT_AT(SPLIT(insured_name, ' '), -1) AS last_name,
        city,
        provider,
        insured_id,
        amount_claimed
    FROM claims_2025
)
SELECT
    last_name,
    city,
    provider,
    COUNT(DISTINCT insured_id) AS unique_members,
    COUNT(*) AS total_claims,
    SUM(amount_claimed) AS total_amount
FROM family_data
GROUP BY last_name, city, provider
HAVING COUNT(DISTINCT insured_id) >= 3
   AND COUNT(*) >= 8
ORDER BY total_claims DESC;


-- ===== 10. התפלגות לפי עיר =====
SELECT
    city,
    COUNT(*) AS claims,
    COUNT(DISTINCT insured_id) AS insured,
    ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT insured_id), 1) AS claims_per_insured
FROM claims_2025
GROUP BY city
ORDER BY claims DESC;


-- ===== 11. היסטוגרמת סכומים =====
SELECT
    CASE
        WHEN amount_claimed < 200 THEN '0-200'
        WHEN amount_claimed < 500 THEN '200-500'
        WHEN amount_claimed < 1000 THEN '500-1000'
        WHEN amount_claimed < 2000 THEN '1000-2000'
        WHEN amount_claimed < 3000 THEN '2000-3000'
        ELSE '3000+'
    END AS amount_range,
    COUNT(*) AS claims
FROM claims_2025
GROUP BY 1
ORDER BY
    CASE amount_range
        WHEN '0-200' THEN 1
        WHEN '200-500' THEN 2
        WHEN '500-1000' THEN 3
        WHEN '1000-2000' THEN 4
        WHEN '2000-3000' THEN 5
        ELSE 6
    END;


-- ===== 12. ציון סיכון למבוטחים =====
WITH person_stats AS (
    SELECT
        insured_name,
        insured_id,
        COUNT(*) AS claims_count,
        COUNT(DISTINCT provider) AS providers_used,
        SUM(amount_claimed) AS total_amount
    FROM claims_2025
    GROUP BY insured_name, insured_id
),
avg_stats AS (
    SELECT AVG(claims_count) AS avg_claims FROM person_stats
)
SELECT
    p.insured_name,
    p.insured_id,
    p.claims_count,
    p.providers_used,
    p.total_amount,
    CASE
        WHEN p.claims_count > a.avg_claims * 10 THEN 40
        WHEN p.claims_count > a.avg_claims * 5 THEN 25
        WHEN p.claims_count > a.avg_claims * 3 THEN 15
        ELSE 0
    END +
    CASE
        WHEN p.providers_used = 1 THEN 20
        WHEN p.providers_used = 2 THEN 10
        ELSE 0
    END AS risk_score
FROM person_stats p
CROSS JOIN avg_stats a
WHERE (p.claims_count > a.avg_claims * 3) OR (p.providers_used = 1 AND p.claims_count > 5)
ORDER BY risk_score DESC, claims_count DESC
LIMIT 30;
