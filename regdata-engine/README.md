# RegData Engine

## Components

- Apache Kafka
- Apache Spark 3.5.9
- PySpark
- Apache Iceberg
- Amazon S3
- AWS Glue Data Catalog

## Output tables

- lake.regdata.raw_transactions
- lake.regdata.clean_transactions
- lake.regdata.quarantine_transactions
- lake.regdata.batch_metrics

## Start application

spark-submit ... main.py

## Checkpoint

~/regdata-checkpoints/transaction-processor
