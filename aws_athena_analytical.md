# Phase 4.F – Amazon Athena Analytics

Amazon Athena is integrated with the AWS Glue Data Catalog and Amazon S3 to enable SQL-based analytical queries over the Apache Iceberg tables created by the Spark processing application.

## Architecture

* **Amazon Athena:** Serverless SQL query engine.
* **AWS Glue Data Catalog:** Stores database and Iceberg table metadata.
* **Amazon S3:** Stores Iceberg metadata and Parquet data files.
* **Athena Query Results:** Stored separately in the S3 `athena-results/` prefix.

---

## Configuration

| Component | Configuration |
| :--- | :--- |
| **AWS Region** | `ap-south-1` |
| **Glue Database** | `regdata` |
| **S3 Warehouse** | `s3://regdata-engine-storage/warehouse/` |
| **Athena Results** | `s3://regdata-engine-storage/athena-results/` |
| **Athena Engine** | Version 3 |

---

## Analytical Views

Seven Athena views were implemented:

1. **`v_aml_high_value`** – Identifies high-value transactions requiring review.
2. **`v_aml_cross_border`** – Identifies cross-border transactions.
3. **`v_aml_kyc_missing`** – Identifies transactions marked with missing KYC.
4. **`v_aml_review_queue`** – Combines transactions requiring compliance review.
5. **`v_daily_summary`** – Provides daily transaction statistics.
6. **`v_dq_quarantine_daily`** – Summarizes quarantined records by error code and date.
7. **`v_pipeline_health`** – Provides batch-level processing and reconciliation information.

---

## SQL Scripts

The `sql/` directory contains:

* **`athena_basic_checks.sql`** – Database, table, and data verification queries.
* **`athena_views.sql`** – SQL definitions of all seven analytical views.
* **`athena_validation.sql`** – Queries for validating analytical views and pipeline metrics.

These views provide a SQL-based analytical layer over the existing Iceberg storage without duplicating the underlying transaction data.