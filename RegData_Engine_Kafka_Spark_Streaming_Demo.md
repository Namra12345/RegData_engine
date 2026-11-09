# RegData Engine: Real-Time Transaction Simulation with Kafka and Spark

## 1. Objective

Build a small virtual financial environment that continuously generates
**30--40 synthetic financial transaction records per second**, publishes
them to **Apache Kafka**, and processes them using **Apache Spark
Structured Streaming**.

The demonstration should show an event-driven data pipeline:

1.  A Python simulator generates financial transactions.
2.  A Kafka producer publishes each transaction to a Kafka topic.
3.  Kafka buffers and distributes the events across topic partitions.
4.  Spark Structured Streaming consumes the events and processes them.
5.  Spark writes validated and normalized records, rejected records, and
    summary statistics to an output destination.

This is a demonstration environment. It uses synthetic data and does not
connect to real banking or payment systems.

## 2. Overall Architecture

``` text
+-------------------------------+
|  Python Transaction Simulator |
|                               |
|  Generates 30–40 records/sec  |
|  Random IDs, amounts, status  |
|  Timestamps and currencies    |
+---------------+---------------+
                |
                | JSON events
                v
+-------------------------------+
|          Kafka Producer       |
|  Publishes transaction events |
+---------------+---------------+
                |
                v
+-------------------------------+
|          Apache Kafka         |
|                               |
| Topic: financial-transactions |
| Partitions: 3 (demo setup)    |
| Buffers and distributes data  |
+---------------+---------------+
                |
                | Kafka connector
                v
+-------------------------------+
|   Spark Structured Streaming  |
|                               |
|  1. Parse JSON                |
|  2. Validate records          |
|  3. Normalize fields          |
|  4. Flag demo conditions      |
|  5. Aggregate over time       |
+---------------+---------------+
                |
                v
+-------------------------------+
|          Output Layer         |
|                               |
|  Processed records            |
|  Rejected records             |
|  Aggregated summaries         |
|  JSON / Parquet / S3          |
+-------------------------------+
```

## 3. Component Responsibilities

### 3.1 Python transaction simulator

The simulator represents a financial source system. It continuously
creates synthetic transactions with randomized values.

Suggested fields:

  Field                Example                  Description
  -------------------- ------------------------ ---------------------------------------------
  `transaction_id`     `TXN-100042`             Unique transaction identifier
  `account_id`         `ACC-7821`               Synthetic account identifier
  `amount`             `2450.75`                Transaction amount
  `currency`           `USD`                    Currency code or intentionally varied input
  `transaction_type`   `PAYMENT`                Type of transaction
  `timestamp`          `2026-10-30T10:15:32Z`   Event timestamp
  `status`             `SUCCESS`                Transaction status

Example JSON event:

``` json
{
  "transaction_id": "TXN-100042",
  "account_id": "ACC-7821",
  "amount": 2450.75,
  "currency": "USD",
  "transaction_type": "PAYMENT",
  "timestamp": "2026-10-30T10:15:32Z",
  "status": "SUCCESS"
}
```

Recommended simulator behavior:

-   Generate a random number of records between 30 and 40 per second.
-   Generate unique transaction IDs.
-   Randomize account IDs, amounts, currencies, transaction types, and
    statuses.
-   Include occasional intentional data-quality issues, such as missing
    values, invalid amounts, or inconsistent currency representations.
-   Print a live counter showing the number of records generated and the
    current generation rate.

Expected volume:

  Period         Approximate records
  ------------ ---------------------
  Per second                  30--40
  Per minute            1,800--2,400
  Per hour          108,000--144,000

The simulator should be independent of Kafka and Spark except for its
producer interface. This makes it easier to test and change the
generation rate without changing the processing logic.

### 3.2 Kafka producer

The Python application acts as a Kafka producer.

Responsibilities:

1.  Create or obtain a transaction event.
2.  Serialize the event as JSON.
3.  Publish it to the Kafka topic `financial-transactions`.
4.  Handle delivery errors and report them.

Suggested Python client: `confluent-kafka`.

### 3.3 Apache Kafka

Kafka is the event-streaming and buffering layer.

Create a topic named:

``` text
financial-transactions
```

For the demonstration, configure three partitions. Kafka partitions
allow records to be distributed and consumed in parallel.

Important distinction:

-   Kafka receives, stores, and distributes events.
-   Kafka does not perform the main financial-data cleaning and
    transformation.
-   Three Kafka partitions do not automatically mean Spark will use
    three separate worker machines. Spark execution and partitioning
    must be configured and verified separately.

### 3.4 Apache Spark Structured Streaming

Spark consumes events from Kafka using the Spark Kafka connector.

Suggested processing stages:

  -----------------------------------------------------------------------
  Stage                               Responsibility
  ----------------------------------- -----------------------------------
  Parse                               Decode Kafka JSON messages into
                                      structured columns

  Validate                            Identify missing transaction IDs,
                                      invalid amounts, or missing
                                      required fields

  Normalize                           Standardize currency
                                      representations, timestamps, and
                                      statuses

  Flag                                Mark records matching demonstration
                                      rules, such as amounts above a
                                      chosen threshold

  Aggregate                           Calculate transaction counts and
                                      total amounts over a time window

  Write                               Save processed records and
                                      summaries to the output layer
  -----------------------------------------------------------------------

Invalid records should be separated into a rejected-record output rather
than silently discarded. Valid records continue through the
normalization pipeline.

A high-value flag in this demonstration is only an illustrative rule. It
is not a complete anti-money-laundering determination.

### 3.5 Output layer

For the first demonstration, Spark can write outputs to JSON or Parquet
files.

Suggested outputs:

-   `processed-transactions/` --- validated and normalized records.
-   `rejected-transactions/` --- records that failed validation, with
    reasons.
-   `transaction-summaries/` --- windowed aggregate counts and amounts.

For the AWS deployment, Amazon S3 can be used as the storage
destination. Apache Iceberg can be considered later if the project needs
lakehouse table management, historical versions, or time-travel queries.

## 4. How the Components Work Together

1.  Start the Python simulator.
2.  The simulator generates 30--40 synthetic records per second.
3.  The Kafka producer publishes each event to `financial-transactions`.
4.  Kafka stores the events in topic partitions.
5.  Spark Structured Streaming subscribes to the Kafka topic.
6.  Spark reads incoming events in streaming micro-batches, parses their
    JSON, and applies the processing rules.
7.  Spark separates valid and invalid records.
8.  Spark writes processed records and summaries to the configured
    output destination.
9.  The demonstration monitors the producer rate, Kafka topic activity,
    and Spark execution.

The key distinction is that **Kafka distributes and buffers events,
while Spark performs distributed computation**.

## 5. Demonstrating Distributed Computing

The presentation should show evidence from each stage:

### Python producer terminal

-   Show the generated transaction records.
-   Show the current records-per-second rate.
-   Show the total records produced.

### Kafka

-   Show that the `financial-transactions` topic is receiving records.
-   Show the topic's partitions and record distribution.
-   Confirm that the consumer can read the published events.

### Spark UI

-   Show the active Structured Streaming query.
-   Show input rows and batch progress.
-   Show stages, tasks, and executors.
-   Verify that executors are running on the intended worker machines.

The Spark UI is particularly important. It helps demonstrate that Spark
is processing work across the configured cluster rather than merely
running on one machine.

### Processed output

-   Show normalized transaction records.
-   Show rejected records and their validation reasons.
-   Show summary counts and total amounts updating as data arrives.

## 6. Suggested Implementation Order

Build and verify the pipeline in small steps.

-   [ ] Create a Python project and virtual environment.
-   [ ] Implement the synthetic transaction generator.
-   [ ] Verify that the generator produces 30--40 records per second.
-   [ ] Run Kafka and create the `financial-transactions` topic.
-   [ ] Connect the Python producer to Kafka.
-   [ ] Verify that Kafka receives the events.
-   [ ] Configure Spark Structured Streaming with the Kafka connector.
-   [ ] Read and parse the Kafka events in Spark.
-   [ ] Implement validation and normalization.
-   [ ] Separate valid and rejected records.
-   [ ] Add a time-window aggregation.
-   [ ] Write the results to JSON or Parquet.
-   [ ] Deploy the components to the AWS demonstration environment.
-   [ ] Verify distributed execution in the Spark UI.
-   [ ] Prepare screenshots or a fallback recording for the
    presentation.

## 7. Suggested Development and Demonstration Setup

A practical approach is to develop locally first and then move the
working pipeline to AWS.

### Local development

Use:

-   Python 3
-   Python `venv`
-   `confluent-kafka`
-   Apache Kafka (for example, through Docker Compose)
-   Apache Spark with the matching Kafka connector
-   JSON or Parquet output

A Python virtual environment isolates Python packages. It is **not** the
same thing as an AWS VPC.

### AWS demonstration

For a short demonstration, a possible arrangement is:

-   A Python simulator running on the developer's laptop or an EC2
    instance.
-   Kafka running on an appropriately configured EC2 instance or small
    cluster.
-   Spark running on a multi-node EC2 Spark cluster.
-   Private network communication between cloud components.
-   S3 for output storage, if required.

Do not expose Kafka broker ports or Spark management interfaces directly
to the public internet. Use private networking, restrictive security
groups, and secure access methods.

The simulator can run on the laptop and publish to Kafka in AWS,
provided the connection is securely configured. This avoids needing a
separate EC2 instance solely for data generation.

## 8. Important Design Notes

-   **Keep components decoupled:** the simulator should generate events;
    the producer should publish them; Spark should process them.
-   **Use synthetic data:** do not use real customer or banking
    information in the demonstration.
-   **Check event-rate measurements:** distinguish records generated per
    second from records successfully delivered to Kafka and records
    processed by Spark.
-   **Avoid data loss:** configure producer delivery handling and Spark
    checkpointing appropriately.
-   **Use durable output:** configure Spark checkpoints and output paths
    so streaming progress can be recovered.
-   **Monitor lag:** compare Kafka production rate with Spark
    consumption and processing rates.
-   **Do not equate partitions with machines:** Kafka partitions, Spark
    partitions, executors, and EC2 instances are related but different
    concepts.
-   **Keep the demo manageable:** 30--40 records per second is a modest
    workload. The purpose is to demonstrate the architecture and
    distributed execution, not to claim enterprise-scale throughput.

## 9. Expected Demonstration Result

At the end of the demonstration, the team should be able to show:

1.  A Python application continuously generating 30--40 synthetic
    financial transactions per second.
2.  Kafka receiving and distributing those events through a topic.
3.  Spark Structured Streaming consuming the topic.
4.  Spark validating, normalizing, flagging, and aggregating the
    transactions.
5.  Results being written to an output destination.
6.  The Spark UI showing the execution details and, when deployed as a
    multi-node cluster, work running across multiple worker machines.

This creates a working demonstration of the RegData Engine
ingestion-and-processing flow:

**Synthetic Financial Data → Kafka → Distributed Spark Processing →
Cleaned and Auditable Outputs**
