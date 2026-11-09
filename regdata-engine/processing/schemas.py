from pyspark.sql.types import (
    StructType,
    StructField,
    StringType
)

TRANSACTION_SCHEMA = StructType([
    StructField("event_id", StringType(), True),
    StructField("transaction_id", StringType(), True),
    StructField("account_id", StringType(), True),
    StructField("customer_name", StringType(), True),
    StructField("kyc_id", StringType(), True),
    StructField("counterparty_account_id", StringType(), True),
    StructField("counterparty_country", StringType(), True),
    StructField("amount", StringType(), True),
    StructField("currency", StringType(), True),
    StructField("transaction_type", StringType(), True),
    StructField("direction", StringType(), True),
    StructField("source", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("status", StringType(), True),
    StructField("merchant_id", StringType(), True),
    StructField("country", StringType(), True),
    StructField("schema_version", StringType(), True)
])
