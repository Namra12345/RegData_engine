-- =============================================================
-- RegData Engine — Phase 4.D Data Checks
-- Run with: spark-sql --master 'local[1]' --driver-memory 512m
--           --properties-file lake.conf -f checks.sql
-- Every query must return 0 rows for the pipeline to be healthy.
-- =============================================================


-- Check 1: Golden rule — records_in must equal records_clean + records_quarantined
-- If this fails, some records were lost or counted twice in a batch.
SELECT batch_id, records_in, records_clean, records_quarantined
FROM lake.regdata.batch_metrics
WHERE records_in <> records_clean + records_quarantined;


-- Check 2: Same Kafka message written twice in raw_transactions
-- MERGE should prevent this. Any row here means MERGE failed.
SELECT source_topic, source_partition, source_offset, COUNT(*) AS n
FROM lake.regdata.raw_transactions
GROUP BY source_topic, source_partition, source_offset
HAVING COUNT(*) > 1;


-- Check 3: Same Kafka message written twice in clean_transactions
-- MERGE should prevent this. Any row here means MERGE failed.
SELECT source_topic, source_partition, source_offset, COUNT(*) AS n
FROM lake.regdata.clean_transactions
GROUP BY source_topic, source_partition, source_offset
HAVING COUNT(*) > 1;


-- Check 4: Same Kafka message present in BOTH clean and quarantine tables
-- A record must go to exactly one table, never both.
SELECT c.source_topic, c.source_partition, c.source_offset
FROM lake.regdata.clean_transactions c
JOIN lake.regdata.quarantine_transactions q
ON  c.source_topic     = q.source_topic
AND c.source_partition = q.source_partition
AND c.source_offset    = q.source_offset;


-- Check 5: Same event_id appearing more than once in clean_transactions
-- Cross-batch duplicate check (Phase 4.B Step 6B) should prevent this.
SELECT event_id, COUNT(*) AS n
FROM lake.regdata.clean_transactions
GROUP BY event_id
HAVING COUNT(*) > 1;


-- Check 6: Same batch recorded more than once in batch_metrics
-- MERGE on batch_id should prevent this.
SELECT batch_id, COUNT(*) AS n
FROM lake.regdata.batch_metrics
GROUP BY batch_id
HAVING COUNT(*) > 1;


-- Check 7: Unknown error codes in quarantine_transactions
-- Only the agreed D7 error codes are allowed.
SELECT DISTINCT code AS unknown_code
FROM lake.regdata.quarantine_transactions
LATERAL VIEW EXPLODE(error_codes) t AS code
WHERE code NOT IN (
    'MALFORMED_JSON',
    'DUPLICATE_EVENT_ID_IN_BATCH',
    'DUPLICATE',
    'MISSING_EVENT_ID',
    'MISSING_TRANSACTION_ID',
    'MISSING_ACCOUNT_ID',
    'MISSING_CUSTOMER_NAME',
    'MISSING_COUNTERPARTY_ACCOUNT',
    'MISSING_AMOUNT',
    'INVALID_AMOUNT',
    'NON_POSITIVE_AMOUNT',
    'INVALID_CURRENCY',
    'INVALID_TRANSACTION_TYPE',
    'INVALID_DIRECTION',
    'INVALID_SOURCE',
    'INVALID_TIMESTAMP',
    'INVALID_STATUS',
    'INVALID_COUNTRY_CODE',
    'INVALID_COUNTERPARTY_COUNTRY',
    'UNSUPPORTED_SCHEMA_VERSION',
    'INVALID_KYC_ID'
);


-- Check 8: Raw record count per batch must match records_in in batch_metrics
-- Verifies that every Kafka message received was counted correctly.
SELECT m.batch_id, m.records_in AS expected, r.n AS actual
FROM lake.regdata.batch_metrics m
JOIN (
    SELECT batch_id, COUNT(*) AS n
    FROM lake.regdata.raw_transactions
    GROUP BY batch_id
) r ON m.batch_id = r.batch_id
WHERE r.n <> m.records_in;


-- Check 9: Compliance flag correctness
-- HIGH_VALUE_REVIEW must be set for all INR transactions >= 50000.
-- CROSS_BORDER_TRANSFER must be set when country != counterparty_country.
SELECT transaction_id, amount, currency, country, counterparty_country, rule_flags
FROM lake.regdata.clean_transactions
WHERE
    -- HIGH_VALUE_REVIEW flag is wrong
    (
        ARRAY_CONTAINS(rule_flags, 'HIGH_VALUE_REVIEW') <>
        (currency = 'INR' AND CAST(amount AS DOUBLE) >= 50000)
    )
    OR
    -- CROSS_BORDER_TRANSFER flag is wrong
    (
        ARRAY_CONTAINS(rule_flags, 'CROSS_BORDER_TRANSFER') <>
        (country <> counterparty_country)
    );


-- Freshness check — not a 0-row check, just shows last write time.
-- Should be within the last few minutes while the stream is running.
SELECT MAX(processed_at) AS last_write
FROM lake.regdata.clean_transactions;
