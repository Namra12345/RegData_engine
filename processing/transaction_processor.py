
from datetime import datetime, timezone
from time import perf_counter

from pyspark import StorageLevel
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType,
    StructField,
    LongType,
    TimestampType,
    StringType
)

from processing.transformations import (
    parse_transactions,
    normalize_transactions
)

from processing.validation import (
    validate_transactions
)

from processing.compliance import (
    add_rule_flags
)

from processing.iceberg_writer import (
    write_iceberg_merge
)


def process_batch(batch_df, batch_id):

    spark = batch_df.sparkSession

    if batch_df.limit(1).count() == 0:
        print(f"Batch {batch_id}: Empty batch.")
        return

    batch_df.persist(StorageLevel.MEMORY_AND_DISK)

    validated_df = None
    clean_df = None
    quarantine_df = None

    started_at = datetime.now(timezone.utc).replace(tzinfo=None)
    start_time = perf_counter()

    try:

        # STEP 1: Count every incoming Kafka message.
        records_in = batch_df.count()

        print(
            f"Batch {batch_id}: Received {records_in} records."
        )

        # STEP 2: Preserve original messages and Kafka metadata.
        raw_df = (
            batch_df
            .select(
                F.col("value").cast("string").alias("raw_payload"),
                F.col("topic").alias("source_topic"),
                F.col("partition").alias("source_partition"),
                F.col("offset").alias("source_offset"),
                F.col("timestamp").alias("kafka_timestamp")
            )
            .withColumn(
                "ingestion_timestamp",
                F.current_timestamp()
            )
            .withColumn(
                "batch_id",
                F.lit(batch_id).cast("long")
            )
        )

        # STEP 3: Write original messages to raw Iceberg table.
        write_iceberg_merge(
            raw_df,
            "lake.regdata.raw_transactions",
            [
                "source_topic",
                "source_partition",
                "source_offset"
            ],
            "raw_batch_view"
        )

        # STEP 4: Parse and normalize.
        parsed_df = parse_transactions(batch_df)

        normalized_df = normalize_transactions(parsed_df)

        # STEP 5: Validate all records.
        validated_df = validate_transactions(
            normalized_df
        ).persist(StorageLevel.MEMORY_AND_DISK)

        # STEP 6: Split into clean and quarantined records.
        clean_df = (
            validated_df
            .filter(F.size("error_codes") == 0)
        )

        quarantine_df = (
            validated_df
            .filter(F.size("error_codes") > 0)
        )

        # STEP 7: Add compliance flags to clean records.
        clean_df = add_rule_flags(clean_df)

        # Set processing status.
        clean_df = clean_df.withColumn(
            "processing_status",
            F.when(
                F.size("rule_flags") > 0,
                F.lit("REVIEW_REQUIRED")
            ).otherwise(
                F.lit("PROCESSED")
            )
        )

        # Add clean-table lineage columns.
        clean_df = (
            clean_df
            .withColumn(
                "processed_at",
                F.current_timestamp()
            )
            .withColumn(
                "batch_id",
                F.lit(batch_id).cast("long")
            )
            .withColumn(
                "processor_version",
                F.lit("1.0.0")
            )
        )

        # Add quarantine metadata.
        quarantine_df = (
            quarantine_df
            .withColumn(
                "quarantined_at",
                F.current_timestamp()
            )
            .withColumn(
                "batch_id",
                F.lit(batch_id).cast("long")
            )
        )

        clean_df = clean_df.persist(
            StorageLevel.MEMORY_AND_DISK
        )

        quarantine_df = quarantine_df.persist(
            StorageLevel.MEMORY_AND_DISK
        )

        # STEP 8: Count output records.
        records_clean = clean_df.count()

        records_quarantined = quarantine_df.count()

        records_flagged = (
            clean_df
            .filter(F.size("rule_flags") > 0)
            .count()
        )

        # STEP 9: Reconcile all input records.
        difference = (
            records_in
            - records_clean
            - records_quarantined
        )

        if difference != 0:

            raise RuntimeError(
                f"Batch {batch_id} reconciliation failed. "
                f"Input={records_in}, "
                f"Clean={records_clean}, "
                f"Quarantine={records_quarantined}, "
                f"Difference={difference}"
            )

        # STEP 10: Prepare exact clean-table schema.
        clean_output = clean_df.select(
            "event_id",
            "transaction_id",
            "account_id",
            "customer_name",
            "kyc_id",
            "counterparty_account_id",
            "counterparty_country",
            "amount",
            "currency",
            "transaction_type",
            "direction",
            "source",
            "timestamp",
            "status",
            "merchant_id",
            "country",
            "schema_version",
            "rule_flags",
            "processing_status",
            "processed_at",
            "source_topic",
            "source_partition",
            "source_offset",
            "batch_id",
            "processor_version"
        )

        # STEP 11: Prepare exact quarantine-table schema.
        quarantine_output = quarantine_df.select(
            "raw_payload",
            "event_id",
            "transaction_id",
            "error_codes",
            "error_details",
            "quarantined_at",
            "source_topic",
            "source_partition",
            "source_offset",
            "batch_id"
        )

        # STEP 12: Write clean transactions.
        write_iceberg_merge(
            clean_output,
            "lake.regdata.clean_transactions",
            [
                "source_topic",
                "source_partition",
                "source_offset"
            ],
            "clean_batch_view"
        )

        # STEP 13: Write quarantined transactions.
        write_iceberg_merge(
            quarantine_output,
            "lake.regdata.quarantine_transactions",
            [
                "source_topic",
                "source_partition",
                "source_offset"
            ],
            "quarantine_batch_view"
        )

        # STEP 14: Create batch metrics.
        completed_at = (
            datetime.now(timezone.utc).replace(tzinfo=None)
        )

        duration_ms = int(
            (perf_counter() - start_time) * 1000
        )

        metrics_schema = StructType([

            StructField("batch_id", LongType(), False),
            StructField("started_at", TimestampType(), False),
            StructField("completed_at", TimestampType(), False),
            StructField("records_in", LongType(), False),
            StructField("records_clean", LongType(), False),
            StructField("records_quarantined", LongType(), False),
            StructField("records_flagged", LongType(), False),
            StructField("reconciliation_difference", LongType(), False),
            StructField("reconciliation_status", StringType(), False),
            StructField("processing_duration_ms", LongType(), False)

        ])

        metrics_df = spark.createDataFrame(
            [(
                int(batch_id),
                started_at,
                completed_at,
                int(records_in),
                int(records_clean),
                int(records_quarantined),
                int(records_flagged),
                int(difference),
                "PASSED",
                int(duration_ms)
            )],
            schema=metrics_schema
        )

        # STEP 15: Write metrics only after other writes succeed.
        write_iceberg_merge(
            metrics_df,
            "lake.regdata.batch_metrics",
            ["batch_id"],
            "metrics_batch_view"
        )

        print(
            f"""
            ========== BATCH {batch_id} ==========
            Incoming records    : {records_in}
            Clean records       : {records_clean}
            Quarantined records : {records_quarantined}
            Flagged records     : {records_flagged}
            Reconciliation      : PASSED
            Duration            : {duration_ms} ms
            ======================================
            """
        )

    finally:

        # Release cached DataFrames.
        if clean_df is not None:
            clean_df.unpersist()

        if quarantine_df is not None:
            quarantine_df.unpersist()

        if validated_df is not None:
            validated_df.unpersist()

        batch_df.unpersist()

