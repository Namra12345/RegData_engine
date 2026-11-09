-- =============================================================
-- RegData Engine — Phase 4.E Maintenance
-- Run with: spark-sql --master 'local[1]' --driver-memory 512m
--           --properties-file lake.conf -f maintenance.sql
-- Run this every time you finish a work session, while stream is stopped.
-- =============================================================


-- Step 1: Merge small data files into larger ones (rows are not changed)
-- 1-minute batches create many tiny files; this combines them for faster reads.
CALL lake.system.rewrite_data_files(table => 'regdata.raw_transactions');
CALL lake.system.rewrite_data_files(table => 'regdata.clean_transactions');
CALL lake.system.rewrite_data_files(table => 'regdata.quarantine_transactions');
CALL lake.system.rewrite_data_files(table => 'regdata.batch_metrics');


-- Step 2: Merge small metadata (manifest) files
-- Each batch also creates a small manifest file; this combines them.
CALL lake.system.rewrite_manifests('regdata.raw_transactions');
CALL lake.system.rewrite_manifests('regdata.clean_transactions');
CALL lake.system.rewrite_manifests('regdata.quarantine_transactions');
CALL lake.system.rewrite_manifests('regdata.batch_metrics');


-- Step 3: Drop snapshot history older than 7 days (keep at least 50 snapshots)
-- Each batch creates a snapshot; old ones waste S3 space.
-- Note: timestamp is calculated as 7 days before today (2026-11-06); update date when re-running.
CALL lake.system.expire_snapshots('regdata.raw_transactions', TIMESTAMP '2026-10-30 00:00:00', 50);
CALL lake.system.expire_snapshots('regdata.clean_transactions', TIMESTAMP '2026-10-30 00:00:00', 50);
CALL lake.system.expire_snapshots('regdata.quarantine_transactions', TIMESTAMP '2026-10-30 00:00:00', 50);
CALL lake.system.expire_snapshots('regdata.batch_metrics', TIMESTAMP '2026-10-30 00:00:00', 50);


-- Step 4: Remove orphan files
-- Note: remove_orphan_files requires Hadoop S3 filesystem support which is only
-- available when running via spark-submit (full cluster mode), not spark-sql local mode.
-- Run this manually via spark-submit if needed, or skip — Steps 1-3 cover the main cleanup.
