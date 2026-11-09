
import os

from config.spark_config import create_spark_session

from processing.iceberg_writer import (
    create_iceberg_namespace,
    create_iceberg_tables
)

from processing.transaction_processor import process_batch


KAFKA_BROKER = "10.0.1.80:9093"

KAFKA_TOPIC = "transactions"

CHECKPOINT_PATH = os.path.expanduser(
    "~/regdata-checkpoints/transaction-processor"
)


def main():

    spark = create_spark_session()

    try:

        # Create Glue namespace.
        create_iceberg_namespace(spark)

        # Create four Iceberg tables.
        create_iceberg_tables(spark)

        print("Iceberg tables initialized.")

        # Read transactions from Kafka.
        kafka_stream = (
            spark.readStream
            .format("kafka")
            .option(
                "kafka.bootstrap.servers",
                KAFKA_BROKER
            )
            .option(
                "subscribe",
                KAFKA_TOPIC
            )
            .option(
                "startingOffsets",
                "latest"
            )
            .option(
                "failOnDataLoss",
                "true"
            )
            .option(
                "maxOffsetsPerTrigger",
                "5000"
            )
            .load()
        )

        # Process Kafka records every minute.
        query = (
            kafka_stream
            .writeStream
            .foreachBatch(process_batch)
            .trigger(
                processingTime="1 minute"
            )
            .option(
                "checkpointLocation",
                CHECKPOINT_PATH
            )
            .start()
        )

        print(
            "RegData Engine transaction processor started."
        )

        query.awaitTermination()

    finally:

        spark.stop()


if __name__ == "__main__":
    main()

