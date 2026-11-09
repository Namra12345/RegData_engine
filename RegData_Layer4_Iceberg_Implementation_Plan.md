# RegData Engine — Layer 4 (Analytical Storage: Apache Iceberg)
## Phase-wise Implementation Plan

| Item | Value |
|---|---|
| Owner | Guru |
| Layer | 4 — Analytical Storage (Apache Iceberg) |
| Input | Spark (Layer 3, friend) writes 4 tables every 1 minute |
| Output | Clean, audit-ready tables for AML views, data-quality reports, pipeline health, and Layers 5 & 6 |
| Cloud | AWS **Mumbai (ap-south-1)** |
| Contract | *RegData Engine: Phase 3 → Phase 4 Handoff* (Oct 30, 2026) |

```
Kafka (Layer 2) ─▶ Spark (Layer 3) ─▶  Iceberg tables (Layer 4)              ─▶ Readers
  on EC2            on EC2              catalog: lake   namespace: regdata
                    1-min batches       ┌───────────────────────────────┐
                                        │ raw_transactions              │      Athena (SQL, no server)
                                        │ clean_transactions   ◀── AML  │ ───▶ FastAPI dashboard (Layer 6)
                                        │ quarantine_transactions       │      Lineage (Layer 5)
                                        │ batch_metrics                 │
                                        │ fx_rates (reference)          │
                                        └───────────────────────────────┘
                                         files: S3 bucket   catalog: AWS Glue
```

---

## ⚠️ Key Decision First: Storage Location

The handoff PDF says **"MinIO locally, S3 later"**. Two problems with that now:

1. **MinIO's free (community) Docker image is no longer published** — `docker pull minio/minio` fails. Only forks/mirrors remain.
2. **Spark runs on EC2.** Storage on a laptop can't be reached by EC2 machines.

### Recommended: S3 + AWS Glue from day one

| Part | Choice | Why |
|---|---|---|
| File storage | **Amazon S3** (one bucket, Mumbai) | Reachable from laptop *and* EC2; no server to run |
| Iceberg catalog | **AWS Glue Data Catalog** | No server to run; free tier covers this project's size |
| Ad-hoc SQL / views | **Amazon Athena** | Query tables without starting Spark; pay only per query |

- Same config works on laptop and on EC2 → **no "switch to S3 later" step**.
- Cost at 40 records/sec is a few cents per day (storage + requests).
- Local-only fallback (no AWS) is in the **Appendix** if ever needed.

### Fix in the PDF
- Bucket name is written two ways (`regdatawarehouse` and `regdata-warehouse`).
- S3 bucket names are **global across all AWS users**, so `regdata-warehouse` is probably taken.
- Use one name everywhere, for example: **`regdata-warehouse-<team-suffix>`** (written below as `<BUCKET>`).

---

## Phase Overview

```
4.1          4.2           4.3              4.4          4.5           4.6            4.7
AWS storage → Create    →  Hand-off kit  →  Data      →  Analytics  →  Maintenance  →  Readers for
setup        tables        to friend        checks       views         & audit         Layers 5 & 6
└──────── DO FIRST (unblocks friend) ───┘
```

| Phase | Goal | Done when |
|---|---|---|
| 4.1 | Bucket, Glue database, permissions ready | You can list the bucket from laptop |
| 4.2 | All 4 tables + `fx_rates` exist | `SHOW TABLES IN lake.regdata` lists 5 tables |
| 4.3 | Friend can write to the tables | Friend's smoke test passes |
| 4.4 | Prove nothing is lost or duplicated | All checks return 0 bad rows |
| 4.5 | AML + quality + health views | Views return data in Athena |
| 4.6 | Fast tables, audit history kept | Daily compaction runs; time-travel demo works |
| 4.7 | Dashboard and lineage can read | FastAPI reads a view |

---

## Phase 4.1 — AWS Storage Setup  *(Day 1)*

### Steps
1. **Create S3 bucket** `<BUCKET>` in **ap-south-1**.
   - Block all public access: **ON** (default)
   - Default encryption: **SSE-S3** (default)
   - Versioning: **OFF** (Iceberg keeps its own history; versioning would double storage)
2. **Folder layout** (created automatically on first write):
   ```
   s3://<BUCKET>/warehouse/            ← Iceberg tables
   s3://<BUCKET>/_checkpoints/phase3/  ← Spark checkpoint (never delete)
   s3://<BUCKET>/athena-results/       ← Athena query output
   ```
3. **Permissions** (ask friend, since he manages IAM):
   - **Laptop:** your IAM user, set with `aws configure` (region `ap-south-1`).
   - **Spark EC2 machines:** attach an **IAM role** (instance profile) — no keys stored on servers.
   - Both need:
     - S3 on `<BUCKET>`: `ListBucket`, `GetBucketLocation`, `GetObject`, `PutObject`, `DeleteObject`
       (Delete is needed for compaction/cleanup of old files — rows are never deleted)
     - Glue: `GetDatabase(s)`, `CreateDatabase`, `GetTable(s)`, `CreateTable`, `UpdateTable`, `DeleteTable`
     - Athena (laptop/dashboard only): run queries, write to `athena-results/`
4. **Optional, free:** add an **S3 Gateway VPC Endpoint** to the Spark VPC so EC2 → S3 traffic stays inside AWS.
5. **Budget alert** already planned in Layer 2 — make sure it covers S3/Glue/Athena too.

**Done when:** `aws s3 ls s3://<BUCKET>/` works from your laptop.

---

## Phase 4.2 — Create the Tables  *(Day 1–2)*

### 4.2.1 Shared Spark config — `lake.conf`
One file used by **you and your friend**, so both talk to the same catalog.

> Versions must match friend's Spark. Example below is for **Spark 3.5 (Scala 2.12)**.
> For Spark 4.0 use `iceberg-spark-runtime-4.0_2.13` and a matching `hadoop-aws` (3.4.x).
> Check the latest Iceberg 1.x release before installing.

```properties
spark.jars.packages  org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.10.0,org.apache.iceberg:iceberg-aws-bundle:1.10.0,org.apache.hadoop:hadoop-aws:3.3.4

# Iceberg catalog "lake" → AWS Glue + S3
spark.sql.extensions                       org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions
spark.sql.catalog.lake                     org.apache.iceberg.spark.SparkCatalog
spark.sql.catalog.lake.catalog-impl        org.apache.iceberg.aws.glue.GlueCatalog
spark.sql.catalog.lake.warehouse           s3://<BUCKET>/warehouse
spark.sql.catalog.lake.io-impl             org.apache.iceberg.aws.s3.S3FileIO
spark.sql.catalog.lake.client.region       ap-south-1

# All timestamps in UTC (PDF rule)
spark.sql.session.timeZone                 UTC

# Allow writing Spark's "nullable" columns into NOT NULL table columns.
# A real null in a NOT NULL column will still fail the write — so Spark must quarantine it first.
spark.sql.iceberg.check-nullability        false

# s3a:// is only for the Spark checkpoint folder
spark.hadoop.fs.s3a.endpoint               s3.ap-south-1.amazonaws.com
spark.hadoop.fs.s3a.aws.credentials.provider  com.amazonaws.auth.DefaultAWSCredentialsProviderChain
```

### 4.2.2 Create-table script — `create_tables.sql`

```sql
CREATE NAMESPACE IF NOT EXISTS lake.regdata;

-- Table 1: every Kafka message, untouched
CREATE TABLE IF NOT EXISTS lake.regdata.raw_transactions (
  event_id         STRING,
  raw_payload      STRING    NOT NULL,
  kafka_topic      STRING    NOT NULL,
  kafka_partition  INT       NOT NULL,
  kafka_offset     BIGINT    NOT NULL,
  kafka_timestamp  TIMESTAMP NOT NULL,
  ingested_at      TIMESTAMP NOT NULL
) USING iceberg
PARTITIONED BY (days(ingested_at))
TBLPROPERTIES ('format-version'='2', 'write.parquet.compression-codec'='zstd');

-- Table 2: fixed records for all analytics and AML
CREATE TABLE IF NOT EXISTS lake.regdata.clean_transactions (
  event_id                 STRING        NOT NULL,
  transaction_id           STRING        NOT NULL,
  account_id               STRING        NOT NULL,
  customer_name            STRING        NOT NULL,
  kyc_id                   STRING,
  counterparty_account_id  STRING        NOT NULL,
  counterparty_country     STRING        NOT NULL,
  merchant_id              STRING,
  amount                   DECIMAL(18,2) NOT NULL,
  currency                 STRING        NOT NULL,
  amount_inr               DECIMAL(18,2) NOT NULL,
  direction                STRING        NOT NULL,
  transaction_type         STRING        NOT NULL,
  source                   STRING        NOT NULL,
  status                   STRING        NOT NULL,
  country                  STRING        NOT NULL,
  device_id                STRING,
  event_time               TIMESTAMP     NOT NULL,
  event_date               DATE          NOT NULL,
  schema_version           INT           NOT NULL,
  -- rule flags
  is_high_value            BOOLEAN       NOT NULL,
  is_cross_border          BOOLEAN       NOT NULL,
  is_kyc_missing           BOOLEAN       NOT NULL,
  -- lineage
  batch_id                 BIGINT        NOT NULL,
  processed_at             TIMESTAMP     NOT NULL,
  pipeline_version         STRING        NOT NULL
) USING iceberg
PARTITIONED BY (days(event_time))
TBLPROPERTIES ('format-version'='2', 'write.parquet.compression-codec'='zstd');

-- Table 3: rejected records + reason
CREATE TABLE IF NOT EXISTS lake.regdata.quarantine_transactions (
  event_id         STRING,
  transaction_id   STRING,
  kafka_topic      STRING    NOT NULL,
  kafka_partition  INT       NOT NULL,
  kafka_offset     BIGINT    NOT NULL,
  raw_payload      STRING    NOT NULL,
  error_reason     STRING    NOT NULL,
  error_field      STRING,
  schema_version   INT,
  batch_id         BIGINT    NOT NULL,
  processed_at     TIMESTAMP NOT NULL
) USING iceberg
PARTITIONED BY (days(processed_at))
TBLPROPERTIES ('format-version'='2', 'write.parquet.compression-codec'='zstd');

-- Table 4: one row per Spark batch (small → no partitioning)
CREATE TABLE IF NOT EXISTS lake.regdata.batch_metrics (
  batch_id             BIGINT    NOT NULL,
  batch_started_at     TIMESTAMP NOT NULL,
  batch_finished_at    TIMESTAMP NOT NULL,
  records_in           BIGINT    NOT NULL,
  records_clean        BIGINT    NOT NULL,
  records_quarantined  BIGINT    NOT NULL,
  pipeline_version     STRING    NOT NULL
) USING iceberg
TBLPROPERTIES ('format-version'='2');

-- Reference: currency rates for amount_inr
CREATE TABLE IF NOT EXISTS lake.regdata.fx_rates (
  currency     STRING        NOT NULL,
  rate_to_inr  DECIMAL(18,6) NOT NULL,
  valid_from   TIMESTAMP     NOT NULL
) USING iceberg
TBLPROPERTIES ('format-version'='2');

-- Prototype fixed rates — EXAMPLE NUMBERS ONLY, team must agree the real values
INSERT INTO lake.regdata.fx_rates VALUES
  ('INR', 1.000000,   TIMESTAMP '2026-01-01 00:00:00'),
  ('USD', 88.000000,  TIMESTAMP '2026-01-01 00:00:00'),
  ('EUR', 102.000000, TIMESTAMP '2026-01-01 00:00:00'),
  ('GBP', 117.000000, TIMESTAMP '2026-01-01 00:00:00');
```

### 4.2.3 Run it (from laptop)
```bash
spark-sql --properties-file lake.conf -f create_tables.sql
spark-sql --properties-file lake.conf -e "SHOW TABLES IN lake.regdata"
```

**Done when:** 5 tables are listed, and they also show up in the **AWS Glue console** under database `regdata`.

---

## Phase 4.3 — Hand-off Kit to Friend  *(Day 2 — unblocks Layer 3)*

### What you give him (matches "What Phase 4 gives Phase 3" in the PDF)
| Item | File / Value |
|---|---|
| Storage | `s3://<BUCKET>/warehouse` (replaces MinIO) |
| Catalog config | `lake.conf` |
| Table scripts | `create_tables.sql` (already run — he only appends) |
| FX rates | `lake.regdata.fx_rates` |
| Checkpoint path | `s3a://<BUCKET>/_checkpoints/phase3/` |
| Smoke test | `smoke_test.py` (below) |

### Smoke test — `smoke_test.py`
Writes to a **scratch table**, so the real audit tables stay clean.

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("lake-smoke-test").getOrCreate()  # run with: spark-submit --properties-file lake.conf

spark.sql("CREATE TABLE IF NOT EXISTS lake.regdata.zz_smoke_test (id INT, note STRING) USING iceberg")
spark.sql("INSERT INTO lake.regdata.zz_smoke_test VALUES (1, 'hello from spark')")
print(spark.sql("SELECT * FROM lake.regdata.zz_smoke_test").collect())
print(spark.sql("SELECT COUNT(*) FROM lake.regdata.fx_rates").collect())
spark.sql("DROP TABLE lake.regdata.zz_smoke_test PURGE")
print("PASS — Spark can read and write the lake")
```

### Points to agree with friend (not in the PDF yet)
1. **Add `batch_id` to `raw_transactions`.** Then "every raw message = clean + quarantine" can be checked per batch with one simple query.
2. **Write order inside `foreachBatch`:** raw → clean → quarantine → **batch_metrics last**.
   On restart, Spark may re-run the last batch with the same `batch_id`. If that `batch_id` is already in `batch_metrics`, **skip the batch** — so nothing is written twice.
3. **DUPLICATE routing:** a watermark de-dup simply *drops* repeats. To send them to quarantine as `DUPLICATE`, Spark must check incoming `transaction_id`s against `clean_transactions` (last 1 hour) inside `foreachBatch`.
4. **Bucket name and MinIO → S3 change** (above).
5. **Spark and Scala versions**, so `lake.conf` packages match.

**Done when:** friend runs `smoke_test.py` on his machine and on one EC2 Spark machine — both PASS.

---

## Phase 4.4 — Data Checks  *(after first real batches)*

Save as `checks.sql`. **Every query should return 0 rows.** Run after each test run, later on a schedule.

```sql
-- 1. Golden rule per batch: in = clean + quarantined
SELECT batch_id FROM lake.regdata.batch_metrics
WHERE records_in <> records_clean + records_quarantined;

-- 2. transaction_id must be unique in clean
SELECT transaction_id, COUNT(*) AS n FROM lake.regdata.clean_transactions
GROUP BY transaction_id HAVING COUNT(*) > 1;

-- 3. Same message must not be in both clean and quarantine (DUPLICATE copies excluded)
SELECT q.event_id FROM lake.regdata.quarantine_transactions q
JOIN lake.regdata.clean_transactions c ON q.event_id = c.event_id
WHERE q.error_reason <> 'DUPLICATE';

-- 4. Same Kafka message written twice to raw (batch replay)
SELECT kafka_topic, kafka_partition, kafka_offset, COUNT(*) AS n
FROM lake.regdata.raw_transactions
GROUP BY 1,2,3 HAVING COUNT(*) > 1;

-- 5. Same batch recorded twice
SELECT batch_id, COUNT(*) AS n FROM lake.regdata.batch_metrics
GROUP BY batch_id HAVING COUNT(*) > 1;

-- 6. Unknown error codes in quarantine
SELECT DISTINCT error_reason FROM lake.regdata.quarantine_transactions
WHERE error_reason NOT IN ('MALFORMED_JSON','SCHEMA_DRIFT','DUPLICATE','MISSING_ACCOUNT',
  'NEGATIVE_AMOUNT','INVALID_CURRENCY','INVALID_TIMESTAMP','MISSING_MERCHANT','INVALID_VALUE');

-- 7. Rule flags are correct
SELECT transaction_id FROM lake.regdata.clean_transactions
WHERE is_high_value   <> (amount_inr >= 1000000)
   OR is_cross_border <> (country <> counterparty_country);

-- 8. (needs batch_id in raw) every raw message accounted for
-- SELECT m.batch_id FROM lake.regdata.batch_metrics m
-- JOIN (SELECT batch_id, COUNT(*) n FROM lake.regdata.raw_transactions GROUP BY batch_id) r
--   ON m.batch_id = r.batch_id
-- WHERE r.n <> m.records_in;
```

Plus one **freshness** check (should return a recent time while the pipeline runs):
```sql
SELECT MAX(batch_finished_at) AS last_batch FROM lake.regdata.batch_metrics;
```

**Done when:** a 30-minute run gives 0 bad rows on all checks.

---

## Phase 4.5 — Analytics Views  *(Athena)*

Run in **Athena** (database `regdata`, results to `s3://<BUCKET>/athena-results/`), so the Spark cluster doesn't need to be on just to query.
Keep each view's SQL in the repo under `sql/views/`.

| View | Built from | Shows |
|---|---|---|
| `v_aml_high_value` | clean | Transactions ≥ ₹10,00,000 |
| `v_aml_cross_border` | clean | Country ≠ counterparty country |
| `v_aml_kyc_missing` | clean | Missing/invalid PAN |
| `v_aml_review_queue` | clean | Rows with **any** flag, + how many flags (most risky first) |
| `v_daily_summary` | clean | Count and ₹ total per day / type / status |
| `v_dq_quarantine_daily` | quarantine | Rejected count per day per error code |
| `v_pipeline_health` | batch_metrics | Per batch: counts, duration, golden-rule pass/fail |

Example:
```sql
CREATE OR REPLACE VIEW v_aml_review_queue AS
SELECT transaction_id, account_id, customer_name, amount_inr, country, counterparty_country, event_time,
       is_high_value, is_cross_border, is_kyc_missing,
       CAST(is_high_value AS INT) + CAST(is_cross_border AS INT) + CAST(is_kyc_missing AS INT) AS flag_count
FROM clean_transactions
WHERE is_high_value OR is_cross_border OR is_kyc_missing;

CREATE OR REPLACE VIEW v_pipeline_health AS
SELECT batch_id, batch_started_at, batch_finished_at,
       date_diff('second', batch_started_at, batch_finished_at) AS duration_sec,
       records_in, records_clean, records_quarantined,
       records_in = records_clean + records_quarantined AS check_passed
FROM batch_metrics;
```

**Done when:** all 7 views return data in Athena.

---

## Phase 4.6 — Maintenance & Audit Features

1-minute batches create many small files (~1,440 commits per table per day). Small files make queries slow.

### Daily maintenance job (`maintenance.sql`, run once a day with `spark-sql`)
```sql
-- Merge small files into bigger ones (rows are not changed)
CALL lake.system.rewrite_data_files(table => 'regdata.raw_transactions');
CALL lake.system.rewrite_data_files(table => 'regdata.clean_transactions');
CALL lake.system.rewrite_data_files(table => 'regdata.quarantine_transactions');

-- Remove old history snapshots (keeps 7 days of time travel)
CALL lake.system.expire_snapshots(table => 'regdata.clean_transactions',
                                  older_than => current_timestamp() - INTERVAL 7 DAYS,
                                  retain_last => 50);
-- (repeat for the other 3 tables)

-- Delete files no table points to any more
CALL lake.system.remove_orphan_files(table => 'regdata.clean_transactions');
```
Run it while the stream is **paused**, or at a quiet time, to avoid write conflicts.

### Audit features to demo
- **Time travel** — "show the data as it was at report time":
  ```sql
  SELECT COUNT(*) FROM lake.regdata.clean_transactions TIMESTAMP AS OF '2026-11-05 10:00:00';
  ```
- **Tags** — freeze the exact data behind a filed report, kept even after snapshot cleanup:
  ```sql
  ALTER TABLE lake.regdata.clean_transactions CREATE TAG `sar_report_2026_11` RETAIN 3650 DAYS;
  ```
- **History** — who wrote what, when:
  ```sql
  SELECT * FROM lake.regdata.clean_transactions.snapshots;
  ```

**Done when:** maintenance runs without errors, and time travel + tag demo work.

---

## Phase 4.7 — Readers for Layers 5 & 6

| Reader | How it reads Layer 4 |
|---|---|
| **Dashboard (FastAPI, Layer 6)** | Athena via `boto3` (or PyIceberg + Glue for small reads) — query the views, not raw tables |
| **Lineage (Layer 5)** | `event_id` → `raw_transactions` → Kafka address; `batch_id` + `pipeline_version` → Spark run and git commit |
| **Compliance reports** | Build from `v_aml_*` views; tag the snapshot used for each filed report |

**Done when:** one FastAPI endpoint returns rows from `v_pipeline_health`.

---

## Hand-off Checklist (Layer 4 → Layer 3)
- [ ] Bucket `<BUCKET>` created in ap-south-1
- [ ] IAM: your user + EC2 role have S3 + Glue access
- [ ] `lake.conf` shared, versions matched to friend's Spark
- [ ] 4 tables + `fx_rates` created
- [ ] FX rate values agreed
- [ ] Checkpoint path shared
- [ ] Points 1–5 in Phase 4.3 agreed with friend
- [ ] Friend's smoke test PASS (laptop + EC2)

## Cost Checklist
- [ ] One S3 bucket, versioning OFF
- [ ] Glue catalog (free tier at this size)
- [ ] Athena for queries instead of keeping Spark on
- [ ] Daily compaction (fewer files = cheaper, faster queries)
- [ ] Budget alert covers S3 / Glue / Athena

---

## Appendix — Local-only Fallback (no AWS)

Use only if you must work offline. Replace S3 + Glue with:

| Part | Local choice |
|---|---|
| Object storage | **RustFS** or **`pgsty/minio`** (community MinIO fork) — official MinIO image is gone |
| Catalog | **Postgres** with Iceberg JDBC catalog |

Config lines that change in `lake.conf`:
```properties
spark.sql.catalog.lake.type                jdbc
spark.sql.catalog.lake.uri                 jdbc:postgresql://localhost:5432/iceberg_catalog
spark.sql.catalog.lake.jdbc.user           iceberg
spark.sql.catalog.lake.jdbc.password       iceberg
spark.sql.catalog.lake.warehouse           s3://regdata-warehouse/warehouse
spark.sql.catalog.lake.s3.endpoint         http://localhost:9000
spark.sql.catalog.lake.s3.path-style-access true
spark.hadoop.fs.s3a.endpoint               http://localhost:9000
spark.hadoop.fs.s3a.path.style.access      true
# remove catalog-impl GlueCatalog line; add org.postgresql:postgresql to spark.jars.packages
```
Tables, checks and views stay exactly the same.
