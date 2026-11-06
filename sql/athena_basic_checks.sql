
-- ============================================
-- RegData Engine: Athena Basic Checks
-- Phase 4.F
-- ============================================

-- 1. List available Glue databases
SHOW SCHEMAS FROM AwsDataCatalog;

-- 2. List tables in RegData database
SHOW TABLES IN regdata;

-- 3. Inspect table schemas
DESCRIBE regdata.raw_transactions;

DESCRIBE regdata.clean_transactions;

DESCRIBE regdata.quarantine_transactions;

DESCRIBE regdata.batch_metrics;

-- 4. Count raw transactions
SELECT COUNT(*)
FROM regdata.raw_transactions;

-- 5. Count clean transactions
SELECT COUNT(*)
FROM regdata.clean_transactions;

-- 6. Count quarantined transactions
SELECT COUNT(*)
FROM regdata.quarantine_transactions;

-- 7. Inspect sample clean transactions
SELECT *
FROM regdata.clean_transactions
LIMIT 10;

-- 8. Inspect sample quarantined transactions
SELECT *
FROM regdata.quarantine_transactions
LIMIT 10;

-- 9. Inspect batch metrics
SELECT *
FROM regdata.batch_metrics
ORDER BY batch_id DESC
LIMIT 10;
