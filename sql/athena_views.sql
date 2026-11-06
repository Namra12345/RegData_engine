
-- ============================================
-- RegData Engine: Athena Analytical Views
-- Phase 4.F
-- Database: regdata
-- ============================================


-- VIEW 1: High-value transactions

CREATE OR REPLACE VIEW regdata.v_aml_high_value AS
SELECT *
FROM regdata.clean_transactions
WHERE contains(rule_flags, 'HIGH_VALUE_REVIEW');


-- VIEW 2: Cross-border transactions

CREATE OR REPLACE VIEW regdata.v_aml_cross_border AS
SELECT *
FROM regdata.clean_transactions
WHERE contains(rule_flags, 'CROSS_BORDER_TRANSFER');


-- VIEW 3: Missing KYC transactions

CREATE OR REPLACE VIEW regdata.v_aml_kyc_missing AS
SELECT *
FROM regdata.clean_transactions
WHERE contains(rule_flags, 'KYC_MISSING');


-- VIEW 4: Compliance review queue

CREATE OR REPLACE VIEW regdata.v_aml_review_queue AS
SELECT
    event_id,
    transaction_id,
    account_id,
    customer_name,
    kyc_id,
    amount,
    currency,
    country,
    counterparty_country,
    timestamp,
    rule_flags,
    processing_status
FROM regdata.clean_transactions
WHERE
    contains(rule_flags, 'HIGH_VALUE_REVIEW')
    OR contains(rule_flags, 'CROSS_BORDER_TRANSFER')
    OR contains(rule_flags, 'KYC_MISSING');


-- VIEW 5: Daily transaction summary

CREATE OR REPLACE VIEW regdata.v_daily_summary AS
SELECT
    DATE(timestamp) AS transaction_date,
    transaction_type,
    status,
    currency,
    COUNT(*) AS total_transactions,
    SUM(amount) AS total_amount,
    SUM(
        CASE
            WHEN contains(rule_flags, 'HIGH_VALUE_REVIEW')
            THEN 1 ELSE 0
        END
    ) AS high_value_transactions,
    SUM(
        CASE
            WHEN contains(rule_flags, 'CROSS_BORDER_TRANSFER')
            THEN 1 ELSE 0
        END
    ) AS cross_border_transactions
FROM regdata.clean_transactions
GROUP BY
    DATE(timestamp),
    transaction_type,
    status,
    currency;


-- VIEW 6: Daily quarantine summary

CREATE OR REPLACE VIEW regdata.v_dq_quarantine_daily AS
SELECT
    DATE(quarantined_at) AS quarantine_date,
    error_code,
    COUNT(*) AS total_quarantined_records
FROM regdata.quarantine_transactions
CROSS JOIN UNNEST(error_codes) AS t(error_code)
GROUP BY
    DATE(quarantined_at),
    error_code;


-- VIEW 7: Pipeline health

CREATE OR REPLACE VIEW regdata.v_pipeline_health AS
SELECT
    batch_id,
    started_at,
    completed_at,
    records_in,
    records_clean,
    records_quarantined,
    records_flagged,
    reconciliation_difference,
    reconciliation_status,
    processing_duration_ms,
    CASE
        WHEN reconciliation_status = 'PASS'
        THEN 'HEALTHY'
        ELSE 'CHECK_REQUIRED'
    END AS pipeline_health
FROM regdata.batch_metrics;
