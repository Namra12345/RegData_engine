
-- ============================================
-- RegData Engine: Athena Validation
-- Phase 4.F
-- ============================================

-- 1. Verify all analytical views
SHOW VIEWS IN regdata;


-- 2. Test high-value transactions
SELECT *
FROM regdata.v_aml_high_value
LIMIT 10;


-- 3. Test cross-border transactions
SELECT *
FROM regdata.v_aml_cross_border
LIMIT 10;


-- 4. Test missing KYC transactions
SELECT *
FROM regdata.v_aml_kyc_missing
LIMIT 10;


-- 5. Test compliance review queue
SELECT *
FROM regdata.v_aml_review_queue
LIMIT 10;


-- 6. Test daily transaction summary
SELECT *
FROM regdata.v_daily_summary
LIMIT 10;


-- 7. Test daily quarantine summary
SELECT *
FROM regdata.v_dq_quarantine_daily
LIMIT 10;


-- 8. Test pipeline health
SELECT *
FROM regdata.v_pipeline_health
LIMIT 10;


-- 9. Verify compliance flag distribution
SELECT
    flag,
    COUNT(*) AS total_records
FROM regdata.clean_transactions
CROSS JOIN UNNEST(rule_flags) AS t(flag)
GROUP BY flag
ORDER BY total_records DESC;


-- 10. Verify batch reconciliation
SELECT
    batch_id,
    records_in,
    records_clean,
    records_quarantined,
    reconciliation_difference,
    reconciliation_status
FROM regdata.batch_metrics
ORDER BY batch_id DESC
LIMIT 20;
