# RegData Engine

## Implementation and Technical Documentation --- Current Project Status

**Document type:** Implementation and Technical Documentation\
**Project:** RegData Engine\
**Processing framework:** Apache Spark 3.5.9\
**Streaming platform:** Apache Kafka 3.7.0\
**Table format:** Apache Iceberg 1.9.2\
**Catalog:** AWS Glue Data Catalog\
**Storage:** Amazon S3\
**Application language:** Python / PySpark

------------------------------------------------------------------------

# 1. Project Overview

RegData Engine is a prototype data-engineering platform designed to
demonstrate how financial transaction data can be ingested, processed,
validated, classified, and stored using distributed data-processing
technologies.

The system receives transaction events from a Kafka topic, processes
them using Spark Structured Streaming, applies data-quality and
compliance-oriented checks, and stores the results in Apache Iceberg
tables backed by Amazon S3. AWS Glue Data Catalog is used to maintain
the catalog metadata for those tables.

The main objectives are to:

-   Ingest a continuous stream of synthetic financial transaction
    events.
-   Process transaction data using a distributed Spark cluster.
-   Preserve incoming records for traceability.
-   Normalize and validate transaction fields.
-   Separate valid records from invalid or incomplete records.
-   Apply demonstration compliance flags to valid transactions.
-   Store raw, clean, quarantined, and batch-level metric data.
-   Use Iceberg table management on top of Amazon S3 storage.
-   Demonstrate a cloud-based streaming data-engineering architecture.

**Scope note:** This is an academic and technical prototype. Its
validation rules and compliance flags are illustrative and must not be
represented as a complete regulatory reporting, AML, or production
banking solution.

# 2. Implemented Architecture

The implementation consists of three main environments:

1.  A local machine that generates synthetic transaction events.
2.  An AWS EC2-based Kafka and Spark processing environment.
3.  AWS managed storage and catalog services.

## 2.1 Architecture Diagram

``` text
                  LOCAL MACHINE
             Python Transaction Generator
                         |
                         | Kafka Producer
                         v
                +--------------------+
                |     KAFKA EC2      |
                |  Apache Kafka 3.7  |
                |  Topic:            |
                |  transactions      |
                +--------------------+
                         |
                         | Structured Streaming
                         v
          +--------------------------------------+
          |          APACHE SPARK CLUSTER        |
          |                                      |
          |  Spark Master EC2                    |
          |  - Spark Master service              |
          |  - Spark application driver          |
          |                                      |
          |  Spark Worker EC2 - 1                |
          |  Spark Worker EC2 - 2                |
          |  - Distributed task execution        |
          +--------------------------------------+
                         |
                         | Spark + Iceberg
                         v
          +--------------------------------------+
          |          AWS GLUE CATALOG            |
          |                                      |
          |  Database / Namespace: regdata      |
          |  Catalog name: lake                  |
          |  Iceberg table metadata registration|
          +--------------------------------------+
                         |
                         | Table data and metadata
                         v
          +--------------------------------------+
          |             AMAZON S3                |
          |                                      |
          |  regdata-engine-storage              |
          |  warehouse/                          |
          |    raw_transactions/                 |
          |    clean_transactions/               |
          |    quarantine_transactions/          |
          |    batch_metrics/                    |
          +--------------------------------------+
```

## 2.2 EC2 Distribution

The project uses four EC2 instances:

  -----------------------------------------------------------------------
  Instance role                       Responsibility
  ----------------------------------- -----------------------------------
  Kafka EC2                           Runs Apache Kafka and hosts the
                                      `transactions` topic

  Spark Master EC2                    Runs the Spark Master service and
                                      the application driver in client
                                      deploy mode

  Spark Worker EC2 - 1                Executes distributed Spark tasks

  Spark Worker EC2 - 2                Executes distributed Spark tasks
  -----------------------------------------------------------------------

The Spark Master and both Worker instances were aligned to Apache Spark
3.5.9. Java 17 is used on the Spark instances.

## 2.3 End-to-End Data Flow

1.  The local Python generator creates synthetic financial transaction
    events.
2.  The producer publishes those events to the Kafka topic
    `transactions`.
3.  Spark Structured Streaming reads events from Kafka.
4.  Spark processes incoming data in micro-batches.
5.  The raw input records and Kafka source coordinates are retained.
6.  JSON records are parsed, normalized, and validated.
7.  Valid records are separated from invalid records.
8.  Demonstration compliance flags are applied to valid records.
9.  Raw, clean, quarantine, and batch metric data are written to Iceberg
    tables.
10. Iceberg stores data and table metadata in the S3 warehouse, while
    Glue maintains catalog registration.

# 3. Technology Stack and Component Responsibilities

  -----------------------------------------------------------------------
  Technology                          Role in RegData Engine
  ----------------------------------- -----------------------------------
  Python                              Synthetic transaction generation
                                      and PySpark application logic

  Apache Kafka 3.7.0                  Event streaming and buffering
                                      between producer and processing
                                      application

  Apache Spark 3.5.9                  Distributed processing engine

  Spark Structured Streaming          Continuous ingestion and
                                      micro-batch processing

  PySpark                             Python interface for Spark
                                      processing

  Apache Iceberg 1.9.2                Table format and metadata
                                      management

  Amazon S3                           Persistent storage for Parquet data
                                      files and Iceberg metadata

  AWS Glue Data Catalog               Catalog and table registration

  AWS EC2                             Compute infrastructure for Kafka
                                      and Spark

  IAM instance role                   Temporary AWS credentials and
                                      permissions for EC2 applications
  -----------------------------------------------------------------------

## 3.1 Apache Kafka

Kafka acts as the streaming ingestion layer. The Python generator
publishes transaction events to the `transactions` topic. Spark consumes
the topic through its Kafka source integration.

Kafka decouples transaction generation from downstream processing. The
producer and Spark application do not need to run as one program or at
exactly the same speed.

Kafka source coordinates such as topic, partition, and offset are
important for tracing individual records and supporting replay-aware
processing.

## 3.2 Apache Spark and Structured Streaming

Apache Spark is the distributed processing engine. Structured Streaming
provides a DataFrame-based API for reading streaming data from Kafka and
processing it in micro-batches.

The application uses `foreachBatch` to invoke the transaction-processing
function for each micro-batch. This allows the project to apply ordinary
DataFrame transformations and write each processed batch to Iceberg.

The configured processing trigger is one minute. This is a trigger
interval, not a guarantee that every batch will finish within exactly 60
seconds.

## 3.3 Apache Iceberg

Apache Iceberg is the table format used to manage the project's
analytical tables.

Iceberg provides table metadata and snapshot management on top of data
files stored in object storage. It tracks the files belonging to a table
and records table changes through metadata and snapshots.

For this project:

-   Spark performs the transformations and writes.
-   Iceberg manages table metadata, manifests, and snapshots.
-   Parquet is used for the table data files.
-   Amazon S3 stores the data and Iceberg metadata files.
-   AWS Glue provides the catalog used to locate and register tables.

Iceberg is not itself the object-storage service or the processing
engine. It is the table-management layer between Spark and the
underlying storage.

## 3.4 Amazon S3

Amazon S3 is the persistent storage layer. The project warehouse is:

``` text
s3://regdata-engine-storage/warehouse/
```

The Iceberg tables use separate table locations under the warehouse.
Iceberg writes Parquet data files and its associated metadata files to
S3.

The S3 bucket should remain private, with Block Public Access enabled
and access controlled through IAM.

## 3.5 AWS Glue Data Catalog

AWS Glue Data Catalog maintains the catalog information used by the
Iceberg Spark catalog.

The configured namespace/database is `regdata`, and the Spark catalog
name is `lake`.

Glue stores catalog registration and table metadata references. The
actual Parquet data files and Iceberg metadata files are stored in S3.

Therefore, Glue and S3 serve different purposes:

-   Glue helps Spark discover and identify tables.
-   S3 stores the table data and Iceberg metadata objects.

# 4. Transaction Data Schema

The synthetic transaction generator produces transaction events with the
following 17 fields.

  -----------------------------------------------------------------------
  Field                               Purpose
  ----------------------------------- -----------------------------------
  `event_id`                          Identifies an individual
                                      event/message and supports
                                      event-level lineage and duplicate
                                      checks

  `transaction_id`                    Business identifier of the
                                      transaction

  `account_id`                        Account associated with the
                                      transaction

  `customer_name`                     Synthetic customer name; normalized
                                      during processing

  `kyc_id`                            Synthetic PAN-like identifier used
                                      for demonstration validation

  `counterparty_account_id`           Account identifier of the other
                                      party

  `counterparty_country`              Country associated with the
                                      counterparty

  `amount`                            Transaction amount

  `currency`                          Currency code associated with the
                                      amount

  `transaction_type`                  Type such as UPI, CARD,
                                      BANK_TRANSFER, or PAYMENT

  `direction`                         Indicates DEBIT or CREDIT

  `source`                            Origin channel such as MOBILE_APP,
                                      WEB_APP, or PAYMENT_GATEWAY

  `timestamp`                         Transaction event timestamp

  `status`                            Transaction status such as SUCCESS,
                                      FAILED, or PENDING

  `merchant_id`                       Merchant identifier, where
                                      applicable

  `country`                           Country associated with the
                                      transaction context

  `schema_version`                    Version marker for the incoming
                                      event schema
  -----------------------------------------------------------------------

## 4.1 Important Field Distinctions

-   `event_id` identifies an individual event, while `transaction_id`
    identifies the business transaction. A repeated business transaction
    ID and a repeated event ID are not necessarily the same condition.
-   `country` describes the transaction's own country context, while
    `counterparty_country` describes the other party's country.
-   `schema_version` allows the pipeline to identify the event schema
    version. The currently supported versions are 1 and 2, which are
    treated as compatible with the implemented schema.

## 4.2 Synthetic Data and Validation Limitations

The data is synthetic and intended for demonstrating data-engineering
behavior.

The PAN-like `kyc_id` check validates a pattern only; it does not verify
a real person's identity or genuine KYC status. Similarly, a two-letter
country-code pattern check does not establish that a code is an
authoritative or currently valid country code.

Customer-name normalization is limited to basic text cleanup and does
not infer or rearrange a person's name.

# 5. Application Code Structure

The application is organized into modules so that configuration, schema
definitions, transformations, validation, compliance rules, and storage
logic remain separate.

``` text
regdata-engine/
├── config/
│   ├── __init__.py
│   └── spark_config.py
├── processing/
│   ├── __init__.py
│   ├── schemas.py
│   ├── transformations.py
│   ├── validation.py
│   ├── compliance.py
│   ├── iceberg_writer.py
│   └── transaction_processor.py
├── main.py
└── README.md
```

## 5.1 `config/spark_config.py`

This module contains Spark session and catalog configuration.

Its responsibilities include:

-   Creating the Spark session.
-   Enabling the Iceberg Spark SQL extension.
-   Registering the `lake` Spark catalog.
-   Configuring AWS Glue as the catalog implementation.
-   Configuring the S3 warehouse location and Iceberg S3 file I/O.
-   Setting the application name and relevant Spark settings.

The EC2 IAM role supplies AWS credentials to the application. Long-term
AWS access keys should not be embedded in the source code.

## 5.2 `processing/schemas.py`

This module defines the schema used to interpret incoming transaction
JSON.

The initial input schema is tolerant of incoming JSON values being
represented as strings. Later transformation logic performs the required
type conversions and validation.

Keeping schema definitions separate makes it easier to maintain and
evolve the expected event structure.

## 5.3 `processing/transformations.py`

This module handles parsing and normalization.

Its responsibilities include:

-   Parsing the Kafka message value as JSON.
-   Retaining the original JSON payload as a string for traceability.
-   Extracting Kafka topic, partition, offset, and Kafka timestamp
    metadata.
-   Normalizing text fields.
-   Converting the amount to a decimal representation.
-   Parsing the transaction timestamp.
-   Converting the schema version to its expected numeric type.
-   Identifying records that cannot be parsed or converted correctly.

The retained raw payload is the original JSON content represented as a
string; it is not a byte-for-byte binary capture of the Kafka message.

## 5.4 `processing/validation.py`

This module applies data-quality checks to the normalized records.

The checks include:

-   Required-field validation.
-   Amount validity checks.
-   Allowed currency values.
-   Allowed transaction types.
-   Allowed transaction directions.
-   Allowed source channels.
-   Allowed transaction statuses.
-   Timestamp parsing and validity.
-   Synthetic KYC identifier pattern validation.
-   Country-code shape validation.
-   Supported schema-version validation.
-   Duplicate `event_id` detection within the current micro-batch.

Records that fail the implemented validation checks are routed to the
quarantine table.

**Deduplication limitation:** The current duplicate `event_id` check is
scoped to a single micro-batch. It does not provide persistent
cross-batch deduplication for an event ID that reappears later in
another batch.

## 5.5 `processing/compliance.py`

This module applies demonstration compliance-oriented flags to valid
records.

The current flags include:

  -----------------------------------------------------------------------
  Flag                                Meaning
  ----------------------------------- -----------------------------------
  `CROSS_BORDER_TRANSFER`             Indicates a transaction involving
                                      different country contexts

  `HIGH_VALUE_REVIEW`                 Indicates an amount above the
                                      demonstration threshold

  `FAILED_TRANSACTION`                Indicates a transaction with FAILED
                                      status

  `PENDING_TRANSACTION`               Indicates a transaction with
                                      PENDING status
  -----------------------------------------------------------------------

The high-value demonstration rule uses a threshold of ₹50,000 for INR
transactions. This is a project-specific example, not an official or
universal AML reporting threshold. The current implementation does not
perform foreign-exchange conversion to normalize amounts across
currencies.

Flagged valid records remain in the clean transaction output. A
compliance flag does not automatically make a record invalid or send it
to quarantine.

## 5.6 `processing/iceberg_writer.py`

This module manages Iceberg table creation and writes.

Its responsibilities include:

-   Creating the `regdata` namespace if required.
-   Creating the four Iceberg tables if they do not already exist.
-   Writing DataFrames to the relevant Iceberg tables.
-   Using Kafka source coordinates for replay-aware record matching in
    the relevant MERGE operations.
-   Writing batch metrics using the batch identifier.

For raw, clean, and quarantine records, the source topic, partition, and
offset are used as the record identity for the implemented merge logic.
These coordinates identify a Kafka record location and help avoid
writing the same source record twice when a batch is retried.

The metrics table uses the Spark batch identifier as its key.

## 5.7 `processing/transaction_processor.py`

This module contains the main micro-batch processing function,
`process_batch(batch_df, batch_id)`.

The high-level responsibilities are:

1.  Persist the incoming micro-batch where appropriate.
2.  Count the input records.
3.  Write the raw records.
4.  Parse and normalize the incoming payloads.
5.  Apply data-quality validation.
6.  Split records into valid and invalid groups.
7.  Apply compliance flags to valid records.
8.  Write valid records to the clean table.
9.  Write invalid records to the quarantine table.
10. Calculate batch-level processing metrics.
11. Reconcile the input count with the clean and quarantine counts.
12. Write the batch metrics.
13. Unpersist the cached batch.

The expected reconciliation is:

``` text
records_in = records_clean + records_quarantined
```

Compliance-flagged records are a subset of the clean records. They are
not a third mutually exclusive output category.

## 5.8 `main.py`

This is the application's entry point.

It is responsible for:

-   Creating the Spark session.
-   Initializing the Iceberg namespace and tables.
-   Defining the Kafka streaming source.
-   Reading the `transactions` topic.
-   Configuring the streaming checkpoint.
-   Connecting the stream to `process_batch` through `foreachBatch`.
-   Starting the streaming query.

The configured Kafka source uses `startingOffsets=latest` for a new
query and `maxOffsetsPerTrigger=5000`. The checkpoint directory used by
the application is:

``` text
~/regdata-checkpoints/transaction-processor
```

When a valid checkpoint already exists, Spark uses the checkpointed
progress rather than treating `startingOffsets` as a fresh starting
position.

# 6. Iceberg Table Design

The application creates four Iceberg tables in the `regdata` namespace.

  ----------------------------------------------------------------------------
  Table                                    Purpose
  ---------------------------------------- -----------------------------------
  `lake.regdata.raw_transactions`          Retains incoming transaction
                                           records and source metadata

  `lake.regdata.clean_transactions`        Stores normalized and validated
                                           records, including any compliance
                                           flags

  `lake.regdata.quarantine_transactions`   Stores records that fail parsing or
                                           validation

  `lake.regdata.batch_metrics`             Stores batch-level counts and
                                           processing/reconciliation metrics
  ----------------------------------------------------------------------------

## 6.1 Raw Transactions

This table preserves the incoming record representation and relevant
Kafka source metadata. It provides a reference point for investigating
how a record entered the pipeline.

## 6.2 Clean Transactions

This table stores records that pass the implemented parsing and
validation rules. Compliance flags can be attached to these records for
downstream review or analysis.

## 6.3 Quarantine Transactions

This table stores records that cannot be processed as valid transactions
under the current rules. Quarantine data is useful for troubleshooting,
data-quality analysis, and understanding why incoming events were
rejected.

## 6.4 Batch Metrics

This table stores processing metrics for each micro-batch. The metrics
include input and output counts and are used to check whether the batch
reconciliation condition holds.

# 7. Processing and Storage Behavior

## 7.1 Micro-Batch Processing

Spark Structured Streaming reads data from Kafka and invokes the
processing function for each micro-batch.

The application is configured with:

-   Kafka topic: `transactions`
-   Maximum offsets per trigger: `5000`
-   Trigger interval: one minute
-   Processing callback: `foreachBatch(process_batch)`
-   Checkpoint directory: `~/regdata-checkpoints/transaction-processor`

The configured trigger interval controls when Spark attempts to start a
micro-batch. Actual batch duration depends on input volume, available
resources, transformations, and storage write time.

## 7.2 Replay and Write Handling

The Iceberg writer uses Kafka source coordinates for the relevant MERGE
operations. This helps the application handle retries of the same Kafka
records without blindly appending duplicate rows.

However, the four table writes are separate table operations. They do
not form one atomic transaction across all four tables. If the
application fails after one table has been committed but before the
others are written, the tables may temporarily reflect partial progress
until retry/recovery logic completes.

The current implementation should therefore be described as replay-aware
and retry-conscious, not as a globally atomic multi-table transaction
system.

## 7.3 Checkpoint Handling

The checkpoint stores streaming progress and is important for restart
behavior.

Do not delete or replace the checkpoint directory casually. Starting the
query with a new checkpoint can cause Spark to treat it as a new
streaming query. In that case, `startingOffsets=latest` can cause the
new query to begin from the latest available Kafka offsets rather than
replaying earlier events.

The batch identifier can also be reused if the query is restarted with a
new checkpoint. For longer-lived or multiple-query operation, a separate
query/run identifier should be considered in the metrics key.

# 8. AWS Storage and Catalog Configuration

## 8.1 S3 Warehouse

The project uses the following S3 bucket and warehouse prefix:

``` text
Bucket:    regdata-engine-storage
Warehouse: s3://regdata-engine-storage/warehouse/
```

The warehouse contains the data and Iceberg metadata directories for the
four tables.

## 8.2 Glue Catalog

The configured Spark catalog is named `lake`.

The namespace/database is:

``` text
regdata
```

The table identifiers are:

``` text
lake.regdata.raw_transactions
lake.regdata.clean_transactions
lake.regdata.quarantine_transactions
lake.regdata.batch_metrics
```

## 8.3 IAM Access

The Spark EC2 instances use the IAM role:

``` text
RegDataSparkEC2Role
```

The role is intended to provide the application with access to the
required S3 and Glue resources through temporary instance credentials.

Avoid storing long-term AWS credentials in application files or source
control. Permissions should be limited to the resources and operations
required by the project.

# 9. Spark Application Dependencies

The application uses the following Maven packages when submitted:

``` text
org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.9
org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.9.2
org.apache.iceberg:iceberg-aws-bundle:1.9.2
```

These provide:

-   Spark's Kafka source integration.
-   Iceberg runtime support for the Spark version and Scala binary
    version.
-   Iceberg AWS integration, including S3 file I/O support.

The Spark Master and Worker nodes must use compatible Spark versions.
The project resolved an earlier mismatch and verified Spark 3.5.9 across
the cluster.

# 10. Application Packaging and Submission

The Python modules required by executors are packaged into a ZIP
archive:

``` bash
zip -r regdata_app.zip config processing
```

The main entry point `main.py` is submitted separately. The `--py-files`
option distributes the ZIP archive containing the application modules to
the executors.

The application is submitted in client deploy mode. In this mode, the
driver runs on the machine from which `spark-submit` is executed---in
this project, the Spark Master EC2 instance. The Spark Master service
itself is not the driver.

The following is the detached submission pattern used by the project.
Confirm the Spark Master private IP before running it if the instance
has changed.

``` bash
nohup bash -c '
export PYSPARK_PYTHON=python3
export PYSPARK_DRIVER_PYTHON=python3
spark-submit \
  --master spark://10.0.1.27:7077 \
  --deploy-mode client \
  --driver-memory 512m \
  --executor-memory 512m \
  --executor-cores 1 \
  --total-executor-cores 2 \
  --py-files regdata_app.zip \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.9,org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.9.2,org.apache.iceberg:iceberg-aws-bundle:1.9.2 \
  --conf spark.driver.host=10.0.1.27 \
  --conf spark.driver.bindAddress=0.0.0.0 \
  --conf spark.driver.port=7078 \
  --conf spark.blockManager.port=7079 \
  --conf spark.executor.cores=1 \
  --conf spark.cores.max=2 \
  --conf spark.pyspark.python=python3 \
  main.py
' > spark_job.log 2>&1 &
```

The memory and core values above are the resource settings used in the
current demonstration setup. They should be reviewed against the actual
EC2 instance capacity before being increased.

## 10.1 Monitoring the Application

Run the following commands on the Spark Master EC2 instance.

Follow the application log:

``` bash
tail -f spark_job.log
```

View the latest log lines:

``` bash
tail -n 100 spark_job.log
```

Search for errors and exceptions:

``` bash
grep -i "error\|exception" spark_job.log
```

Check whether the submission process is running:

``` bash
ps -ef | grep '[s]park-submit'
```

The Spark Master web UI can also be used to inspect registered workers,
available resources, and running applications.

# 11. Implementation and Verification Status

The following table distinguishes completed implementation work from
verification that is still pending.

  -----------------------------------------------------------------------
  Component or milestone              Current status
  ----------------------------------- -----------------------------------
  Synthetic transaction generator     Implemented

  Kafka topic and producer flow       Configured and used

  Kafka-to-Spark connectivity         Working; configured by teammate

  Spark Master and two Workers        Running and connected

  Spark version consistency           Spark 3.5.9 verified across nodes

  Spark transaction-processing        Implemented and deployed
  application                         

  Parsing and normalization           Implemented

  Data-quality validation             Implemented

  Compliance demonstration flags      Implemented

  Raw, clean, quarantine, and metrics Created/verified
  table definitions                   

  Iceberg integration                 Configured

  S3 data writes                      Parquet files observed in S3

  Glue catalog registration           Four table schemas observed

  SQL queries against all four        Not yet completed
  Iceberg tables                      

  End-to-end count reconciliation     Pending
  through table queries               

  Production-scale performance and    Not completed
  resilience testing                  
  -----------------------------------------------------------------------

## 11.1 What Has Been Verified

-   The Spark Master and both Worker nodes are using Spark 3.5.9.
-   The two Spark Workers are registered as alive in the Spark cluster
    dashboard.
-   Kafka-to-Spark connectivity is working.
-   The application has been deployed to the Spark Master and submitted
    to the cluster.
-   The application has processed generated transaction events.
-   Parquet data files have been observed in the S3 warehouse.
-   The Glue `regdata` database and the four table schemas have been
    observed.

## 11.2 Verification Still Required

The next verification milestone is to query the Iceberg tables and
confirm their contents and counts.

The following SQL statements are examples of checks to run from a Spark
SQL session configured with the same Iceberg catalog:

``` sql
SELECT COUNT(*) FROM lake.regdata.raw_transactions;

SELECT COUNT(*) FROM lake.regdata.clean_transactions;

SELECT COUNT(*) FROM lake.regdata.quarantine_transactions;

SELECT *
FROM lake.regdata.batch_metrics
ORDER BY batch_id DESC;
```

The expected count relationship for a completed batch is:

``` text
records_in = records_clean + records_quarantined
```

These SQL queries have not yet been confirmed as executed. The existence
of S3 files and Glue table schemas is useful evidence of setup and
writes, but querying the tables is the next step for verifying readable
table contents and reconciliation.

# 12. Known Limitations and Future Improvements

The current implementation is a working prototype. The following
limitations should be considered before describing it as
production-ready.

1.  **Synthetic data:** Events are generated for demonstration and do
    not represent real customer or banking records.
2.  **Illustrative validation:** KYC and country checks validate simple
    patterns rather than authoritative external sources.
3.  **Demonstration compliance rules:** The flags and ₹50,000 INR
    threshold are examples, not official regulatory rules.
4.  **No currency normalization:** Amounts in different currencies are
    not converted to a common base currency before threshold
    comparisons.
5.  **Micro-batch duplicate scope:** Duplicate `event_id` detection is
    currently limited to a single micro-batch.
6.  **Separate table commits:** Writes to the four Iceberg tables are
    not one atomic cross-table transaction.
7.  **Metrics run identity:** Batch IDs can be reused when a new
    checkpoint/query is created; a durable run or query identifier would
    improve separation.
8.  **Schema evolution:** The application recognizes schema versions 1
    and 2, but a full schema registry and comprehensive compatibility
    policy are not part of the current implementation.
9.  **Operational resilience:** Production-grade alerting, automated
    recovery, capacity planning, and disaster-recovery testing are
    outside the current scope.
10. **Performance validation:** The configured cluster and resource
    settings have not been established as production throughput
    benchmarks.

Potential future improvements include persistent event-level
deduplication, schema registry integration, stronger validation against
authoritative reference data, currency conversion, configurable rule
management, richer observability, automated tests, and performance/load
testing.

# 13. Important Operational Notes

## 13.1 Preserve the Checkpoint

The checkpoint directory maintains the streaming query's progress. Do
not delete it unless intentionally creating a new streaming query and
accepting the resulting offset behavior.

## 13.2 Keep Spark Versions Aligned

The Master and Worker nodes should use compatible Spark distributions.
The current cluster uses Spark 3.5.9.

## 13.3 Protect AWS Resources

Keep the S3 bucket private and restrict IAM permissions. Avoid
committing credentials or secrets to the source repository.

## 13.4 Monitor AWS Costs

EC2 instances and other AWS resources can continue to incur charges.
Stop instances when the demonstration environment is not required, and
separately review billable storage, public IP addresses, snapshots, and
other resources. Stopping an EC2 instance does not automatically delete
its EBS volumes or every associated resource.

# 14. Conclusion

RegData Engine demonstrates an end-to-end streaming data-engineering
workflow for synthetic financial transaction events.

A local Python generator publishes events to Kafka. A distributed Apache
Spark cluster consumes and processes those events using Structured
Streaming. The application parses and normalizes the records, applies
data-quality checks, separates valid and invalid data, and adds
demonstration compliance flags. The resulting datasets are written to
Iceberg tables backed by Amazon S3, with AWS Glue Data Catalog providing
table registration.

The core infrastructure, streaming integration, processing modules,
Iceberg configuration, and initial S3/Glue writes have been implemented
and observed. The next important validation step is to query all four
Iceberg tables and verify their contents, counts, and batch
reconciliation.

The project provides practical experience with event streaming,
distributed processing, data-quality pipelines, cloud object storage,
table formats, and catalog integration while clearly distinguishing a
functional academic prototype from a production regulatory platform.
