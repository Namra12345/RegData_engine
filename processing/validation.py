from pyspark.sql import functions as F
from pyspark.sql.window import Window


def validate_transactions(df):

    def error_if(condition, field, code, message):

        return F.when(
            condition & (~F.col("parse_failed")),
            F.struct(
                F.lit(field).alias("field_name"),
                F.lit(code).alias("error_code"),
                F.lit(message).alias("message")
            )
        )

    details = [

        F.when(
            F.col("parse_failed"),
            F.struct(
                F.lit("$record").alias("field_name"),
                F.lit("MALFORMED_JSON").alias("error_code"),
                F.lit("Message could not be parsed as JSON").alias("message")
            )
        ),

        error_if(
            F.col("event_id").isNull() |
            (F.trim(F.col("event_id")) == ""),
            "event_id",
            "MISSING_EVENT_ID",
            "event_id is required"
        ),

        error_if(
            F.col("transaction_id").isNull() |
            (F.trim(F.col("transaction_id")) == ""),
            "transaction_id",
            "MISSING_TRANSACTION_ID",
            "transaction_id is required"
        ),

        error_if(
            F.col("account_id").isNull() |
            (F.trim(F.col("account_id")) == ""),
            "account_id",
            "MISSING_ACCOUNT_ID",
            "account_id is required"
        ),

        error_if(
            F.col("customer_name").isNull() |
            (F.trim(F.col("customer_name")) == ""),
            "customer_name",
            "MISSING_CUSTOMER_NAME",
            "customer_name is required"
        ),

        error_if(
            F.col("counterparty_account_id").isNull() |
            (F.trim(F.col("counterparty_account_id")) == ""),
            "counterparty_account_id",
            "MISSING_COUNTERPARTY_ACCOUNT",
            "counterparty_account_id is required"
        ),

        error_if(
            F.col("amount").isNull(),
            "amount",
            "MISSING_AMOUNT",
            "amount is required"
        ),

        error_if(
            F.col("amount").isNotNull() &
            (F.trim(F.col("amount")) != "") &
            (F.expr("try_cast(amount AS double)").isNull()),
            "amount",
            "INVALID_AMOUNT",
            "amount must be a valid decimal number"
        ),

        error_if(
            F.expr("try_cast(amount AS double)").isNotNull() &
            (F.col("amount").cast("double") <= 0),
            "amount",
            "NON_POSITIVE_AMOUNT",
            "amount must be greater than zero"
        ),

        error_if(
            ~F.col("currency").isin(
                "INR", "USD", "EUR", "GBP"
            ) | F.col("currency").isNull(),
            "currency",
            "INVALID_CURRENCY",
            "currency is not supported"
        ),

        error_if(
            ~F.col("transaction_type").isin(
                "UPI", "CARD", "BANK_TRANSFER", "PAYMENT"
            ) | F.col("transaction_type").isNull(),
            "transaction_type",
            "INVALID_TRANSACTION_TYPE",
            "transaction_type is not supported"
        ),

        error_if(
            ~F.col("direction").isin(
                "DEBIT", "CREDIT"
            ) | F.col("direction").isNull(),
            "direction",
            "INVALID_DIRECTION",
            "direction must be DEBIT or CREDIT"
        ),

        error_if(
            ~F.col("source").isin(
                "MOBILE_APP",
                "WEB_APP",
                "PAYMENT_GATEWAY"
            ) | F.col("source").isNull(),
            "source",
            "INVALID_SOURCE",
            "source is not supported"
        ),

        error_if(
            F.col("timestamp").isNull() |
            (
                F.to_timestamp(F.col("timestamp"), "yyyy-MM-dd'T'HH:mm:ss.SSSSSSXXX").isNull() &
                F.to_timestamp(F.col("timestamp"), "yyyy-MM-dd'T'HH:mm:ssXXX").isNull()
            ),
            "timestamp",
            "INVALID_TIMESTAMP",
            "timestamp must be a valid ISO-8601 timestamp"
        ),

        error_if(
            ~F.col("status").isin(
                "SUCCESS", "FAILED", "PENDING"
            ) | F.col("status").isNull(),
            "status",
            "INVALID_STATUS",
            "status is not supported"
        ),

        error_if(
            F.col("kyc_id").isNull() |
            ~F.col("kyc_id").rlike(
                "^[A-Z]{5}[0-9]{4}[A-Z]$"
            ),
            "kyc_id",
            "INVALID_KYC_ID",
            "kyc_id does not match the expected synthetic PAN format"
        ),

        error_if(
            F.col("country").isNull() |
            ~F.col("country").rlike("^[A-Z]{2}$"),
            "country",
            "INVALID_COUNTRY_CODE",
            "country must use a two-letter uppercase code"
        ),

        error_if(
            F.col("counterparty_country").isNull() |
            ~F.col("counterparty_country").rlike("^[A-Z]{2}$"),
            "counterparty_country",
            "INVALID_COUNTERPARTY_COUNTRY",
            "counterparty_country must use a two-letter uppercase code"
        ),

        error_if(
            F.col("schema_version").isNull() |
            ~F.col("schema_version").isin(1, 2),
            "schema_version",
            "UNSUPPORTED_SCHEMA_VERSION",
            "Only schema versions 1 and 2 are supported"
        )

    ]

    # Detect repeated event_id values within this micro-batch.
    event_window = Window.partitionBy("event_id")

    df = df.withColumn(
        "_event_id_count",
        F.count("event_id").over(event_window)
    )

    details.append(
        error_if(
            F.col("event_id").isNotNull() &
            (F.col("_event_id_count") > 1),
            "event_id",
            "DUPLICATE_EVENT_ID_IN_BATCH",
            "event_id appears more than once in this batch"
        )
    )

    result = (
        df
        .withColumn(
            "error_details",
            F.filter(
                F.array(*details),
                lambda x: x.isNotNull()
            )
        )
        .withColumn(
            "error_codes",
            F.transform(
                F.col("error_details"),
                lambda x: x["error_code"]
            )
        )
        .drop("_event_id_count")
    )

    return result
