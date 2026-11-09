# RegData Engine — Phase 5 Implementation Log

**Date:** 2026-11-07
**Author:** Aditya Panchal
**Phase:** Phase 5 — Lineage & Governance
**Approach:** Track B (direct to AWS, no local mock data)

---

## Overview

Phase 5 adds lineage tracking, compliance rules engine, PII masking, audit logging, governance tables, SNS alerts, and OpenLineage integration on top of the existing Phase 4 Iceberg pipeline.

---

## Infrastructure Setup

### I-1 — Launch Marquez EC2

- Launched new EC2 instance `regdata-marquez` (t3.small, 2GB RAM)
- Region: ap-south-1 (Mumbai)
- Same VPC as Kafka and Spark: `vpc-089e13544ffe4655c`
- Public IP: `65.0.182.50`
- Private IP: `10.0.1.64`
- Security group: `regdata-marquez-sg`
- Inbound rules:
  - Port 22 (SSH) — My IP
  - Port 5000 (Marquez API) — My IP + Spark SG (`sg-00fc7a95deed14235`)
  - Port 3000 (Marquez Web UI) — My IP
- Key pair: `RegData-key`

### I-2 — Install Marquez on EC2

Steps followed on `65.0.182.50`:

1. Install Docker:
```bash
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl reset-failed docker.service docker.socket
sudo systemctl start docker.socket
sudo systemctl start docker.service
sudo usermod -aG docker ubuntu && newgrp docker
```

2. Install newer Docker (old version didn't support `docker compose`):
```bash
curl -fsSL https://get.docker.com | sudo sh
```

3. Clone Marquez repo:
```bash
git clone https://github.com/MarquezProject/marquez.git
cd marquez
```

4. Create Marquez config file `/home/ubuntu/marquez.yml`:
```yaml
server:
  applicationConnectors:
    - type: http
      port: 5000
  adminConnectors:
    - type: http
      port: 5001

db:
  driverClass: org.postgresql.Driver
  url: jdbc:postgresql://marquez-db:5432/marquez
  user: marquez
  password: marquez

migrateOnStartup: true
tags: []
```

5. Start containers using Docker network:
```bash
docker network create marquez-net
docker run -d --name marquez-db --network marquez-net \
  -e POSTGRES_USER=marquez -e POSTGRES_PASSWORD=marquez \
  -e POSTGRES_DB=marquez postgres:14
sleep 20
docker run -d --name marquez-api --network marquez-net \
  -p 5000:5000 -p 5001:5001 \
  -v /home/ubuntu/marquez.yml:/usr/src/app/marquez.yml \
  -e MARQUEZ_CONFIG=/usr/src/app/marquez.yml \
  marquezproject/marquez:latest
docker run -d --name marquez-web --network marquez-net \
  -p 3000:3000 \
  -e MARQUEZ_HOST=marquez-api \
  -e MARQUEZ_PORT=5000 \
  -e WEB_PORT=3000 \
  marquezproject/marquez-web:latest
```

6. Marquez Web UI accessible at: `http://65.0.182.50:3000`

---

## Phase 5.1 — YAML Compliance Rules Engine

**Problem:** Rules were hardcoded in `processing/compliance.py`. Adding a new rule required Python code changes.

**Solution:** Moved all rules to YAML. Added a rules engine that reads YAML and builds Spark conditions dynamically.

**Files created/modified:**

- `rules/compliance_rules.yaml` — 5 single-transaction rules:
  - `CROSS_BORDER_TRANSFER` — country != counterparty_country
  - `HIGH_VALUE_REVIEW` — INR amount >= 50000
  - `FAILED_TRANSACTION` — status == FAILED
  - `PENDING_TRANSACTION` — status == PENDING
  - `KYC_MISSING` — kyc_id null or invalid format

- `processing/rules_engine.py` — reads YAML, builds Spark conditions (4 condition types supported)

- `processing/compliance.py` — reduced to 4 lines, calls rules engine

**Benefit:** New rules can be added by editing YAML only — no Python change needed.

---

## Phase 5.2 — Audit Log Table

**Note:** Initially created `audit_log` in wrong database (`regdata`). Corrected in Step 5.B to use `regdata_governance`.

---

## Phase 5.A — Governance Database and Tables

Created in **Athena Query Editor**:

```sql
CREATE DATABASE IF NOT EXISTS regdata_governance
LOCATION 's3://regdata-engine-storage/governance/'
```

Three Iceberg tables created:

**1. compliance_alerts** — stores alerts from compliance engine
```sql
CREATE TABLE regdata_governance.compliance_alerts (
  alert_id string, rule_id string, rule_version int,
  severity string, account_id string, window_start timestamp,
  txn_count int, total_amount decimal(18,2), evidence string,
  status string, data_as_of timestamp, created_at timestamp
)
PARTITIONED BY (day(created_at))
LOCATION 's3://regdata-engine-storage/governance/compliance_alerts/'
TBLPROPERTIES ('table_type' = 'ICEBERG')
```

**2. report_runs** — stores report metadata
```sql
CREATE TABLE regdata_governance.report_runs (
  report_id string, created_at timestamp, created_by string,
  rules_version string, data_as_of timestamp, row_count int,
  file_s3_path string, file_sha256 string, iceberg_tag string
)
LOCATION 's3://regdata-engine-storage/governance/report_runs/'
TBLPROPERTIES ('table_type' = 'ICEBERG')
```

**3. audit_log** — append-only audit trail
```sql
CREATE TABLE regdata_governance.audit_log (
  event_time timestamp, actor string, action string,
  target string, details string
)
PARTITIONED BY (day(event_time))
LOCATION 's3://regdata-engine-storage/governance/audit_log/'
TBLPROPERTIES ('table_type' = 'ICEBERG')
```

---

## Phase 5.B — Fix Audit Log Location

Dropped incorrectly placed table:
```sql
DROP TABLE IF EXISTS regdata.audit_log
```

Removed audit_log creation from `iceberg_writer.py` and audit writing from `transaction_processor.py`.

---

## Phase 5.C — PII Masked Views

Created masked view in `regdata_governance`:

```sql
CREATE OR REPLACE VIEW regdata_governance.v_clean_transactions_masked AS
SELECT
    event_id, transaction_id,
    regexp_replace(account_id, '.{4}$', 'XXXX') AS account_id,
    regexp_replace(customer_name, '(?<=\S)\S', 'X') AS customer_name,
    regexp_replace(kyc_id, '^.{6}', 'XXXXXX') AS kyc_id,
    regexp_replace(counterparty_account_id, '.{4}$', 'XXXX') AS counterparty_account_id,
    ...
FROM regdata.clean_transactions
```

PII fields masked:
- `account_id` — last 4 chars → XXXX
- `customer_name` — all chars except first → X
- `kyc_id` — first 6 chars → XXXXXX
- `counterparty_account_id` — last 4 chars → XXXX

**Verified:** Query returned masked values like `ACC-XXXX`, `FXXXXX HXXX`, `XXXXXX229Z`.

---

## Phase 5.D — Compliance Engine (Cross-Account Rules)

**Location:** `phase5/engine/`

**4 YAML rules created:**

| Rule | File | Severity | Detects |
|------|------|----------|---------|
| R1_VELOCITY | `r1_velocity.yaml` | MEDIUM | >10 transactions per hour per account |
| R2_STRUCTURING | `r2_structuring.yaml` | HIGH | Amounts just under INR 10L limit, 3+ times per day |
| R3_NEW_COUNTRY | `r3_new_country.yaml` | MEDIUM | Account sends to country not seen in last 30 days |
| R4_PASS_THROUGH | `r4_pass_through.yaml` | HIGH | Credit followed by same amount debit within 1 hour |

**Engine:** `phase5/engine/run_rules.py`
- Loads all YAML rules
- Runs each rule as Athena query against real data
- Generates `alert_id` using SHA256 (prevents duplicates on rerun)
- Writes alerts to `regdata_governance.compliance_alerts`
- Writes audit entry to `regdata_governance.audit_log`
- Sends SNS email if any HIGH alerts found

**Config:** `phase5/config/settings.yaml`
- Runner: athena
- Region: ap-south-1
- All thresholds configurable without code change

---

## Phase 5.E — Record Trace

**Location:** `phase5/trace/trace.py`

Given a `transaction_id`, returns full lineage path:
- For clean transactions: all fields + rule flags + Kafka topic/partition/offset + batch_id + raw payload
- For quarantined transactions: error codes + quarantine time + raw payload
- For unknown: NOT_FOUND status

**Tested:**
```bash
python3 phase5/trace/trace.py TXN-6ae02fad81a3
```

Output showed:
- Status: CLEAN
- Rule flags: CROSS_BORDER_TRANSFER
- Kafka partition: 1, offset: 11262, batch: 30
- Full raw JSON payload from Kafka

---

## Phase 5.F — Report Generator

**Location:** `phase5/reports/make_report.py`

Steps per report run:
1. Queries `compliance_alerts` for open HIGH severity alerts
2. Writes CSV to local file
3. Calculates SHA256 hash (tamper detection)
4. Uploads CSV to `s3://regdata-engine-storage/governance/reports/`
5. Records metadata in `report_runs` table
6. Writes audit log entry

**Tested:** Generated report `rpt-2026-11-07-1703` with 262 alerts, uploaded to S3.

---

## Phase 5.H — SNS Alerts

**SNS Topic:** `regdata-alerts`
**ARN:** `arn:aws:sns:ap-south-1:776163183407:regdata-alerts`

Two alert types in `processing/alerts.py`:
- `RECONCILIATION_FAILED` — sent before crashing the batch
- `HIGH_QUARANTINE_RATE` — sent when >30% of batch is quarantined

Compliance engine SNS (in `run_rules.py`):
- Sends one email per run listing all new HIGH alerts only
- Never sends one email per alert (avoids spam)

Email confirmed at: `gurukrupa6401@gmail.com`

---

## Phase 5.I — OpenLineage → Marquez

Added 4 config lines to spark-submit command:

```bash
--packages ...,io.openlineage:openlineage-spark_2.12:1.9.1 \
--conf spark.extraListeners=io.openlineage.spark.agent.OpenLineageSparkListener \
--conf spark.openlineage.transport.type=http \
--conf spark.openlineage.transport.url=http://10.0.1.64:5000 \
--conf spark.openlineage.namespace=regdata
```

**Result:** Marquez Web UI at `http://65.0.182.50:3000` showed:
- 71 lineage events
- 5 datasets tracked
- 11 jobs visible
- Jobs showing START, RUNNING, COMPLETE statuses

---

## Phase 5.J — Scheduled Cron Runs

Set up on Spark Master EC2 (`13.233.24.66`):

```bash
crontab -e
```

Added:
```
*/15 * * * * cd /home/ubuntu/regdata-engine && python3 phase5/engine/run_rules.py >> /home/ubuntu/regdata-engine/compliance_engine.log 2>&1
*/5 * * * * cd /home/ubuntu/regdata-engine && python3 phase5/engine/run_rules.py >> /home/ubuntu/regdata-engine/freshness.log 2>&1
```

- Compliance engine runs every 15 minutes
- Freshness check runs every 5 minutes

---

## B5 — Iceberg Tags on Reports

Got latest snapshot ID from Athena:
```sql
SELECT snapshot_id, committed_at
FROM regdata."clean_transactions$snapshots"
ORDER BY committed_at DESC LIMIT 1
```
Snapshot ID: `1909844179415085926`

Created tag on Spark EC2:
```bash
spark-sql --master local[1] --driver-memory 512m \
  --properties-file lake.conf \
  -e "ALTER TABLE lake.regdata.clean_transactions 
      CREATE TAG rpt_2026_11_07_01 
      AS OF VERSION 1909844179415085926 
      RETAIN 3650 DAYS"
```

Tag verified in refs table — snapshot preserved for 10 years.

---

## B6 — Masked Views on Real Data

Verified masked view returns real data with PII hidden:
```sql
SELECT account_id, customer_name, kyc_id, counterparty_account_id
FROM regdata_governance.v_clean_transactions_masked
LIMIT 5
```

Result confirmed all 4 PII fields properly masked.

---

## Schema Changes Made in Athena

Two columns were missing from Glue schema (added during Phase 4.B but not in Glue):

```sql
ALTER TABLE regdata.clean_transactions ADD COLUMNS (amount_inr DECIMAL(18,2))
ALTER TABLE regdata.batch_metrics ADD COLUMNS (run_id STRING)
```

---

## Files Uploaded to Spark EC2

All files uploaded via SCP to `ubuntu@13.233.24.66`:

| Local Path | EC2 Path |
|---|---|
| `processing/compliance.py` | `~/regdata-engine/processing/` |
| `processing/rules_engine.py` | `~/regdata-engine/processing/` |
| `processing/iceberg_writer.py` | `~/regdata-engine/processing/` |
| `processing/transaction_processor.py` | `~/regdata-engine/processing/` |
| `processing/alerts.py` | `~/regdata-engine/processing/` |
| `config/spark_config.py` | `~/regdata-engine/config/` |
| `rules/compliance_rules.yaml` | `~/regdata-engine/rules/` |
| `phase5/` (entire folder) | `~/regdata-engine/phase5/` |

---

## AWS Resources Used in Phase 5

| Resource | Value |
|---|---|
| Marquez EC2 | `65.0.182.50` (public), `10.0.1.64` (private) |
| Marquez Security Group | `regdata-marquez-sg` |
| SNS Topic | `regdata-alerts` |
| SNS Topic ARN | `arn:aws:sns:ap-south-1:776163183407:regdata-alerts` |
| Governance S3 path | `s3://regdata-engine-storage/governance/` |
| Reports S3 path | `s3://regdata-engine-storage/governance/reports/` |
| Governance Glue DB | `regdata_governance` |

---

## Phase 5 Completion Checklist

| Item | Status |
|---|---|
| I-1: Marquez EC2 launched | ✅ Done |
| I-2: Marquez running (API + Web UI) | ✅ Done |
| 5.A: regdata_governance + 3 tables | ✅ Done |
| 5.B: audit_log moved to correct DB | ✅ Done |
| 5.C: PII masked views | ✅ Done |
| 5.D: Compliance engine (4 YAML rules) | ✅ Done |
| 5.E: Record trace | ✅ Done |
| 5.F: Report generator | ✅ Done |
| 5.H: SNS alerts | ✅ Done |
| 5.I: OpenLineage → Marquez | ✅ Done |
| 5.J: Cron scheduled runs | ✅ Done |
| B5: Iceberg tags on reports | ✅ Done |
| B6: Masked views on real data | ✅ Done |
