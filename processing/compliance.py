from pyspark.sql import functions as F


HIGH_VALUE_INR_THRESHOLD = 50000


def add_rule_flags(df):

    # Safely cast amount to double for proper numeric threshold comparison
    amount_numeric = F.col("amount").cast("double")

    conditions = [

        F.when(
            F.col("country") != F.col("counterparty_country"),
            F.lit("CROSS_BORDER_TRANSFER")
        ),

        F.when(
            (F.col("currency") == "INR") &
            (amount_numeric >= HIGH_VALUE_INR_THRESHOLD),
            F.lit("HIGH_VALUE_REVIEW")
        ),

        F.when(
            F.col("status") == "FAILED",
            F.lit("FAILED_TRANSACTION")
        ),

        F.when(
            F.col("status") == "PENDING",
            F.lit("PENDING_TRANSACTION")
        )

    ]

    return df.withColumn(
        "rule_flags",
        F.filter(
            F.array(*conditions),
            lambda x: x.isNotNull()
        )
    )
