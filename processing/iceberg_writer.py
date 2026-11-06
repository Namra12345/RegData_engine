
def create_iceberg_namespace(spark):

    spark.sql("""
        CREATE NAMESPACE IF NOT EXISTS lake.regdata
    """)


def create_iceberg_tables(spark):

    spark.sql("""
        CREATE TABLE IF NOT EXISTS
        lake.regdata.raw_transactions (

            raw_payload STRING,
            source_topic STRING,
            source_partition INT,
            source_offset BIGINT,
            kafka_timestamp TIMESTAMP,
            ingestion_timestamp TIMESTAMP,
            batch_id BIGINT

        )
        USING iceberg
        TBLPROPERTIES ('format-version'='2')
    """)

    spark.sql("""
        CREATE TABLE IF NOT EXISTS
        lake.regdata.clean_transactions (

            event_id STRING,
            transaction_id STRING,
            account_id STRING,
            customer_name STRING,
            kyc_id STRING,
            counterparty_account_id STRING,
            counterparty_country STRING,
            amount DECIMAL(18,2),
            currency STRING,
            transaction_type STRING,
            direction STRING,
            source STRING,
            timestamp TIMESTAMP,
            status STRING,
            merchant_id STRING,
            country STRING,
            schema_version INT,

            rule_flags ARRAY<STRING>,
            processing_status STRING,
            processed_at TIMESTAMP,

            source_topic STRING,
            source_partition INT,
            source_offset BIGINT,
            batch_id BIGINT,
            processor_version STRING

        )
        USING iceberg
        TBLPROPERTIES ('format-version'='2')
    """)

    spark.sql("""
        CREATE TABLE IF NOT EXISTS
        lake.regdata.quarantine_transactions (

            raw_payload STRING,
            event_id STRING,
            transaction_id STRING,

            error_codes ARRAY<STRING>,

            error_details ARRAY<
                STRUCT<
                    field_name: STRING,
                    error_code: STRING,
                    message: STRING
                >
            >,

            quarantined_at TIMESTAMP,
            source_topic STRING,
            source_partition INT,
            source_offset BIGINT,
            batch_id BIGINT

        )
        USING iceberg
        TBLPROPERTIES ('format-version'='2')
    """)

    spark.sql("""
        CREATE TABLE IF NOT EXISTS
        lake.regdata.batch_metrics (

            batch_id BIGINT,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            records_in BIGINT,
            records_clean BIGINT,
            records_quarantined BIGINT,
            records_flagged BIGINT,
            reconciliation_difference BIGINT,
            reconciliation_status STRING,
            processing_duration_ms BIGINT

        )
        USING iceberg
        TBLPROPERTIES ('format-version'='2')
    """)



def write_iceberg_merge(
    df,
    target_table,
    key_columns,
    view_name
):

    # Skip an empty output.
    if df.limit(1).count() == 0:
        return

    df.createOrReplaceTempView(view_name)

    condition = " AND ".join(
        [
            f"target.`{column}` = source.`{column}`"
            for column in key_columns
        ]
    )

    columns = df.columns

    insert_columns = ", ".join(
        [f"`{column}`" for column in columns]
    )

    insert_values = ", ".join(
        [f"source.`{column}`" for column in columns]
    )

    merge_sql = f"""
        MERGE INTO {target_table} AS target
        USING {view_name} AS source
        ON {condition}

        WHEN NOT MATCHED THEN
        INSERT ({insert_columns})
        VALUES ({insert_values})
    """

    try:
        df.sparkSession.sql(merge_sql)

    finally:
        df.sparkSession.catalog.dropTempView(view_name)

