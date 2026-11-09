from pyspark.sql import functions as F # type: ignore

from processing.schemas import TRANSACTION_SCHEMA # type: ignore


def parse_transactions(batch_df):

    parsed = (
        batch_df
        .withColumn(
            "raw_payload",
            F.col("value").cast("string")
        )
        # Extract the nested 'payload' object from the outer event envelope
        .withColumn(
            "payload_str",
            F.get_json_object(F.col("raw_payload"), "$.payload")
        )
        .withColumn(
            "parsed",
            F.from_json(
                F.col("payload_str"),
                TRANSACTION_SCHEMA
            )
        )
        .withColumn(
            "parse_failed",
            F.col("parsed").isNull()
        )
    )

    result = parsed.select(
        F.col("raw_payload"),
        F.col("topic").alias("source_topic"),
        F.col("partition").alias("source_partition"),
        F.col("offset").alias("source_offset"),
        F.col("timestamp").alias("kafka_timestamp"),
        F.col("parse_failed"),
        F.col("parsed.*")
    )

    return result


def normalize_transactions(df):

    result = (
        df

        # Preserve original amount for error analysis
        .withColumn(
            "amount_raw",
            F.col("amount")
        )

        # Normalize customer name formatting
        .withColumn(
            "customer_name",
            F.upper(
                F.trim(
                    F.regexp_replace(
                        F.col("customer_name"),
                        r"\s+",
                        " "
                    )
                )
            )
        )

        # Standardize text fields
        .withColumn(
            "currency",
            F.upper(F.trim(F.col("currency")))
        )
        .withColumn(
            "transaction_type",
            F.upper(F.trim(F.col("transaction_type")))
        )
        .withColumn(
            "direction",
            F.upper(F.trim(F.col("direction")))
        )
        .withColumn(
            "source",
            F.upper(F.trim(F.col("source")))
        )
        .withColumn(
            "status",
            F.upper(F.trim(F.col("status")))
        )
        .withColumn(
            "country",
            F.upper(F.trim(F.col("country")))
        )
        .withColumn(
            "counterparty_country",
            F.upper(F.trim(F.col("counterparty_country")))
        )
        .withColumn(
            "kyc_id",
            F.upper(F.trim(F.col("kyc_id")))
        )

        # Convert amount safely
        .withColumn(
            "amount",
            F.expr(
                "try_cast(amount_raw AS DECIMAL(18,2))"
            )
        )

        # Convert transaction timestamp (keeping field name as timestamp)
        .withColumn(
            "timestamp",
            F.to_timestamp(
                F.col("timestamp"),
                "yyyy-MM-dd'T'HH:mm:ss.SSSSSSXXX"
            )
        )

        # Convert schema version
        .withColumn(
            "schema_version",
            F.expr(
                "try_cast(schema_version AS INT)"
            )
        )
    )

    return result
