
from pyspark.sql import SparkSession


AWS_REGION = "ap-south-1"

S3_WAREHOUSE = (
    "s3://regdata-engine-storage/warehouse/"
)


def create_spark_session():

    spark = (
        SparkSession.builder
        .appName("RegData-Transaction-Processor")

        # Iceberg integration
        .config(
            "spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions"
        )

        # Catalog named lake, backed by AWS Glue
        .config(
            "spark.sql.catalog.lake",
            "org.apache.iceberg.spark.SparkCatalog"
        )
        .config(
            "spark.sql.catalog.lake.type",
            "glue"
        )
        .config(
            "spark.sql.catalog.lake.warehouse",
            S3_WAREHOUSE
        )
        .config(
            "spark.sql.catalog.lake.io-impl",
            "org.apache.iceberg.aws.s3.S3FileIO"
        )
        .config(
            "spark.sql.catalog.lake.client.region",
            AWS_REGION
        )

        # Consistent timestamp interpretation
        .config(
            "spark.sql.session.timeZone",
            "UTC"
        )

        .getOrCreate()
    )

    return spark

