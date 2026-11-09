# RegData Engine

## Infrastructure Setup and Deployment Guide

**Document type:** Infrastructure and Environment Setup\
**Project:** RegData Engine\
**Cloud provider:** Amazon Web Services (AWS)\
**Processing framework:** Apache Spark 3.5.9\
**Streaming platform:** Apache Kafka 3.7.0\
**Table format:** Apache Iceberg\
**Catalog:** AWS Glue Data Catalog\
**Storage:** Amazon S3

------------------------------------------------------------------------

# 1. Introduction

This document describes the infrastructure setup and deployment process
followed while building the RegData Engine project.

It focuses on how the project's computing environment, distributed
processing cluster, cloud storage, metadata catalog, and Iceberg
integration were configured.

The infrastructure was built using Amazon EC2 instances and AWS managed
services.

The main objectives were:

-   Create a distributed Spark cluster using multiple EC2 instances.
-   Deploy Apache Kafka on a separate EC2 instance.
-   Establish communication between Kafka and Spark.
-   Configure AWS infrastructure for storing processed data.
-   Integrate Apache Spark with Apache Iceberg.
-   Configure AWS Glue as the Iceberg catalog.
-   Configure Amazon S3 as the Iceberg warehouse.
-   Deploy and execute the transaction-processing application on the
    Spark cluster.

# 2. Infrastructure Architecture

The project infrastructure is divided into three main parts:

1.  Local environment for transaction generation.
2.  EC2-based distributed processing infrastructure.
3.  AWS managed storage and metadata services.

## 2.1 Infrastructure Diagram

``` text
                   LOCAL MACHINE
                Python Transaction Generator
                           |
                           | Kafka Producer
                           v
                  +--------------------+
                  |  KAFKA EC2         |
                  |  Apache Kafka      |
                  |  Topic:            |
                  |  transactions      |
                  +--------------------+
                           |
                           | Kafka Consumer Connection
                           v
             +--------------------------------+
             |       APACHE SPARK CLUSTER     |
             |                                |
             |  +--------------------------+  |
             |  | Spark Master EC2         |  |
             |  | Spark Master Service     |  |
             |  | Application Driver      |  |
             |  +--------------------------+  |
             |                                |
             |  +--------------------------+  |
             |  | Spark Worker 1 EC2       |  |
             |  +--------------------------+  |
             |                                |
             |  +--------------------------+  |
             |  | Spark Worker 2 EC2       |  |
             |  +--------------------------+  |
             +--------------------------------+
                           |
                           | Iceberg Table Operations
                           v
                 +----------------------+
                 |   APACHE ICEBERG     |
                 |   Table Management   |
                 +----------------------+
                      |            |
                      v            v
              +-------------+  +----------------+
              | AWS GLUE    |  | AMAZON S3      |
              | Data Catalog|  | Iceberg Files  |
              | Table Schema|  | Parquet Data   |
              | Metadata    |  | Metadata Files |
              +-------------+  +----------------+
```

## 2.2 EC2 Instance Distribution

The project uses four EC2 instances.

  -----------------------------------------------------------------------
  Instance                            Responsibility
  ----------------------------------- -----------------------------------
  Kafka EC2                           Hosts the Kafka broker

  Spark Master EC2                    Hosts the Spark Master service and
                                      application driver

  Spark Worker 1 EC2                  Executes distributed Spark tasks

  Spark Worker 2 EC2                  Executes distributed Spark tasks
  -----------------------------------------------------------------------

The Python transaction generator runs on the local machine and sends
events to Kafka.

The Spark Master coordinates the Spark cluster, while the two worker
instances provide the execution resources.

The application uses Spark Standalone in client deployment mode.
Therefore, the application driver runs on the Spark Master EC2 instance
where `spark-submit` is executed.

# 3. AWS Infrastructure Creation

## 3.1 Creating an AWS Account and Selecting a Region

The first step was to access the AWS Management Console and select the
AWS region in which the project infrastructure would be deployed.

All relevant resources, including EC2 instances, S3 storage, and Glue
catalog resources, should be configured consistently with the intended
region.

The region must also match the region configured in the Spark
application's AWS integration settings.

## 3.2 Creating EC2 Instances

We created four EC2 instances:

-   One instance for Apache Kafka.
-   One instance for the Spark Master.
-   Two instances for Spark Workers.

### Step 1: Open the EC2 Dashboard

1.  Log in to the AWS Management Console.
2.  Search for EC2.
3.  Open the EC2 dashboard.
4.  Select Launch Instance.

### Step 2: Configure the Instance

For each instance, configure:

-   Instance name.
-   Ubuntu Server AMI.
-   Instance type according to available compute and memory
    requirements.
-   Key pair for SSH access.
-   VPC and subnet.
-   Security group.
-   Root EBS storage.

The Spark Master and Worker instances should have sufficient memory and
CPU resources for their respective roles.

For this demonstration, smaller EC2 instances were selected to control
infrastructure costs.

**Note:** Record the actual instance types, storage sizes, subnet IDs,
and availability zones from the AWS Console for the final project
report. They are not assumed in this document.

### Step 3: Launch the Instances

After reviewing the configuration, launch all four instances.

Once the instances are running, note their:

-   Instance IDs.
-   Public IP addresses, where applicable.
-   Private IP addresses.
-   Security group IDs.

Private IP addresses are particularly important because communication
between EC2 instances inside the same VPC should use private networking.

## 3.3 Creating and Configuring Security Groups

Security groups act as virtual firewalls for EC2 instances.

They control which network connections are permitted to reach the
instances.

The project requires communication between:

-   Local transaction generator and Kafka.
-   Kafka and Spark application.
-   Spark Master and Spark Workers.
-   Spark application driver and Spark executors.
-   EC2 instances and AWS services.

The following ports are relevant to the current architecture.

  Port                  Component            Purpose
  --------------------- -------------------- -------------------------------------
  22                    SSH                  Remote administration
  7077                  Spark Master         Spark cluster communication
  8080                  Spark Master UI      Cluster monitoring
  8081                  Spark Worker UI      Worker monitoring
  7078                  Spark Driver         Driver communication
  7079                  Spark BlockManager   BlockManager communication
  Kafka listener port   Kafka                Producer and consumer communication

The actual Kafka listener port must match the broker configuration.

### Recommended Security Group Rules

**Kafka security group**

-   Permit SSH from the administrator's IP.
-   Permit the configured Kafka listener port from the required producer
    and Spark sources.
-   Restrict access to trusted sources rather than allowing unrestricted
    public access.

**Spark security group**

-   Permit SSH from the administrator's IP.
-   Permit Spark Master and Worker communication within the Spark
    cluster.
-   Permit the driver and BlockManager communication ports from the
    cluster.
-   Restrict Spark web interfaces to the administrator's IP.

For Spark communication, allowing the necessary internal traffic between
instances belonging to the Spark security group simplifies cluster
networking. For a production deployment, use more narrowly scoped rules
and controlled port ranges.

**Important:** Do not expose Spark or Kafka administration ports to the
entire internet unless there is a specific and secured reason.

# 4. Configuring Apache Kafka

Apache Kafka was deployed on a dedicated EC2 instance.

The Kafka setup was handled separately from the Spark application
development.

## 4.1 Kafka Installation

The Kafka EC2 instance was prepared with the required Java environment
and Apache Kafka 3.7.0.

The Kafka distribution was downloaded and extracted on the instance.

The Kafka installation directory contains the Kafka binaries and
configuration files.

The broker was configured to listen on the required network interface
and expose the listener used by the transaction generator and Spark
consumer.

The exact listener address, port, and advertised listener configuration
must match the actual Kafka broker configuration.

## 4.2 Creating the Kafka Topic

The project uses the following topic:

``` bash
transactions
```

This topic acts as the communication channel between the transaction
generator and the Spark application.

The Python generator publishes financial transaction events to this
topic.

Spark subscribes to the same topic and consumes the incoming messages.

## 4.3 Kafka--Spark Connectivity

After Kafka and Spark were deployed, the connection between Kafka and
Spark was configured.

The Kafka broker was made accessible to the Spark application through
the configured network listener.

The Spark application uses the Kafka connector dependency:

``` text
org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.9
```

This connector enables Spark Structured Streaming to consume records
from Kafka.

**Verification:** The connection was confirmed when the transaction
generator published records and Spark successfully consumed and
processed them.

# 5. Creating the Apache Spark Cluster

Apache Spark was deployed using the Standalone cluster architecture.

The cluster contains:

-   One Spark Master.
-   Two Spark Workers.

The Spark Master coordinates the cluster, while the workers execute
distributed processing tasks.

## 5.1 Preparing the EC2 Instances

The Spark Master and Worker instances were prepared with:

-   Ubuntu Server.
-   Java 17.
-   Python 3.
-   Apache Spark 3.5.9.
-   Required networking and security group configuration.

The same Spark version must be installed and used across all cluster
nodes.

The project uses Spark 3.5.9 with Scala 2.12 and Java 17.

## 5.2 Installing Java

Java is required by Apache Spark because Spark's core runtime operates
on the Java Virtual Machine.

We used Java 17.

Verify the installation using:

``` bash
java -version
```

The output should indicate Java 17.

## 5.3 Installing Python

Python is required for executing the PySpark application.

Verify Python using:

``` bash
python3 --version
```

The Python environment should be compatible and consistent across the
Spark Master and Worker instances.

## 5.4 Installing Apache Spark

Apache Spark 3.5.9 was installed on the Spark Master and both Worker
instances.

The extracted Spark distribution was made available through the
`/opt/spark` path.

The installation was organized so that the Spark commands could be
executed from the terminal.

Important environment variables include:

``` bash
export SPARK_HOME=/opt/spark
export PATH=$SPARK_HOME/bin:$SPARK_HOME/sbin:$PATH
```

In the Spark Master setup, the actual installation directory was:

``` text
/opt/spark-3.5.9-bin-hadoop3
```

The `/opt/spark` path was configured as a symbolic link to the versioned
installation directory.

Verify the symbolic link using:

``` bash
ls -l /opt/spark
```

Verify the resolved path using:

``` bash
readlink -f /opt/spark
```

Verify the Spark version using:

``` bash
spark-submit --version
```

Expected version:

``` text
Spark 3.5.9
```

## 5.5 Resolving the Spark Version Mismatch

During setup, a version mismatch was identified.

The Spark Master initially reported Spark 3.5.3, while the Worker
instances were using Spark 3.5.9.

Running different Spark versions across cluster nodes can lead to
compatibility problems.

The investigation identified that the Spark Master environment was
referencing an older Spark installation.

The following commands were used to investigate:

``` bash
echo $SPARK_HOME
```

``` bash
which spark-submit
```

``` bash
readlink -f $(which spark-submit)
```

The resolved Spark installation was checked using:

``` bash
ls -l /opt/spark
```

The issue was corrected by ensuring that the Spark Master used the Spark
3.5.9 installation:

``` bash
export SPARK_HOME=/opt/spark-3.5.9-bin-hadoop3
export PATH=$SPARK_HOME/bin:$SPARK_HOME/sbin:$PATH
```

The same Spark version was then verified across the Master and Worker
instances.

**Final result:** The Spark Master and both Workers were successfully
configured to use Spark 3.5.9.

## 5.6 Starting the Spark Master

The Spark Master service was started on the Master EC2 instance.

The standard Standalone startup command is:

``` bash
$SPARK_HOME/sbin/start-master.sh
```

The Master service listens on the configured Spark cluster port.

For this project, the application submission uses:

``` text
spark://10.0.1.27:7077
```

The Master web interface is normally available on port 8080.

The Master UI can be used to inspect:

-   Master status.
-   Connected workers.
-   Available CPU cores.
-   Available memory.
-   Running applications.
-   Completed applications.

## 5.7 Starting the Spark Workers

After starting the Master, both Worker instances were connected to it.

The standard worker startup command is:

``` bash
$SPARK_HOME/sbin/start-worker.sh spark://SPARK_MASTER_PRIVATE_IP:7077
```

Replace `SPARK_MASTER_PRIVATE_IP` with the actual private IP of the
Spark Master.

The command was executed on each Worker instance with the appropriate
Master address.

The workers register themselves with the Master and become available for
application execution.

## 5.8 Verifying the Spark Cluster

The Spark Master web interface was opened to verify cluster status.

The dashboard provides information about connected workers and available
resources.

The expected cluster configuration is:

``` text
Spark Master: 1
Spark Workers: 2
```

Both workers should appear as ALIVE.

The cluster was successfully configured and its dashboard was accessible
from the local machine.

# 6. AWS S3 Setup

Amazon S3 was selected as the underlying storage layer for the Iceberg
tables.

## 6.1 Creating the S3 Bucket

The S3 bucket was created through the AWS Management Console.

The bucket used in the implementation is:

``` text
regdata-engine-storage
```

The bucket is used as the warehouse location for the Iceberg tables.

The warehouse prefix is:

``` text
warehouse/
```

The full warehouse location is:

``` text
s3://regdata-engine-storage/warehouse/
```

### Bucket Configuration

The bucket should be configured with:

-   Block Public Access enabled.
-   Private access.
-   Server-side encryption.
-   Appropriate IAM permissions.
-   The same AWS region used by the Glue catalog and application
    configuration.

The application writes the Iceberg table data and metadata files into
this warehouse.

## 6.2 Understanding the S3 Warehouse

The warehouse is the root storage location used by Iceberg to organize
the tables.

Conceptually, the storage structure is:

``` text
s3://regdata-engine-storage/
│
└── warehouse/
    │
    └── regdata/
        │
        ├── raw_transactions/
        ├── clean_transactions/
        ├── quarantine_transactions/
        └── batch_metrics/
```

Each table has its own managed data and metadata files.

Iceberg controls the exact layout and the files created within each
table directory.

# 7. AWS IAM Role Configuration

The Spark application requires permission to access Amazon S3 and AWS
Glue.

Instead of storing AWS access keys inside the application, an EC2 IAM
role was configured.

## 7.1 Creating the IAM Role

The role used in the project is:

``` text
RegDataSparkEC2Role
```

It is an IAM role intended for EC2 instances.

The role was created with EC2 as its trusted service so that the EC2
instance profile can provide temporary credentials to applications
running on the instances.

## 7.2 Configuring Permissions

The role requires appropriate permissions for S3 and Glue.

### S3 Permissions

The application requires permissions for operations such as:

-   Listing the bucket.
-   Getting bucket location.
-   Reading S3 objects.
-   Writing S3 objects.
-   Managing multipart uploads.

### Glue Permissions

The application requires permissions for operations such as:

-   Getting Glue databases.
-   Creating or updating databases.
-   Getting table definitions.
-   Creating or updating tables.
-   Accessing relevant catalog metadata.

The exact IAM policy should be scoped to the project's bucket and Glue
resources wherever possible.

## 7.3 Attaching the Role to EC2

The role was attached to the Spark EC2 instances through the EC2
instance profile mechanism.

This allows the Spark application to access AWS services using the
permissions associated with the role.

The application does not need AWS access keys hardcoded in Python files.

## 7.4 Verifying AWS Access

The AWS CLI can be used to verify the EC2 instance identity:

``` bash
aws sts get-caller-identity
```

To verify S3 access:

``` bash
aws s3 ls s3://regdata-engine-storage/
```

To verify Glue access:

``` bash
aws glue get-databases --region YOUR_AWS_REGION
```

Replace `YOUR_AWS_REGION` with the region used by the project.

These commands should be executed on an EC2 instance with the configured
role and AWS CLI available.

# 8. AWS Glue Data Catalog Setup

AWS Glue Data Catalog was selected as the metadata catalog for Apache
Iceberg.

It allows Spark and Iceberg to discover table definitions and their
associated metadata locations.

## 8.1 Opening AWS Glue

1.  Open the AWS Management Console.
2.  Search for AWS Glue.
3.  Open the Data Catalog section.
4.  Navigate to Databases.

## 8.2 Creating the Database

The project uses the database/namespace:

``` text
regdata
```

The Glue database is used to organize the project's Iceberg table
definitions.

The application is configured to use this namespace when creating the
tables.

## 8.3 Why Glue Is Required

The Glue Data Catalog stores metadata such as:

-   Database information.
-   Table names.
-   Table schemas.
-   Table metadata locations.

It does not store the actual Parquet transaction data.

The actual files are stored in Amazon S3.

Glue and Iceberg work together so that Spark can discover and access the
tables.

# 9. Apache Iceberg Setup

Apache Iceberg was integrated with Spark to manage the analytical tables
stored in S3.

This section describes the important configuration steps performed to
establish the integration.

## 9.1 Understanding the Integration

The Iceberg integration contains three major components:

  -----------------------------------------------------------------------
  Component                           Responsibility
  ----------------------------------- -----------------------------------
  Apache Iceberg                      Manages table structure, metadata,
                                      snapshots, and table operations

  AWS Glue                            Maintains the catalog information
                                      for the tables

  Amazon S3                           Stores Parquet data and Iceberg
                                      metadata files
  -----------------------------------------------------------------------

Spark acts as the processing engine that reads and writes the Iceberg
tables.

## 9.2 Adding Iceberg Dependencies

The application requires the Iceberg Spark runtime and AWS integration
libraries.

The following dependencies were configured:

``` text
org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.9.2

org.apache.iceberg:iceberg-aws-bundle:1.9.2
```

The Kafka connector was also included:

``` text
org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.9
```

These dependencies were supplied to Spark during application submission
using the `--packages` parameter.

The versions were selected to match the project's Spark 3.5.9 and Scala
2.12 environment.

## 9.3 Configuring the Iceberg Catalog

The Spark session was configured with an Iceberg catalog named:

``` text
lake
```

The catalog uses the AWS Glue Data Catalog implementation.

The configuration includes the following important properties:

``` text
spark.sql.extensions =
org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions

spark.sql.catalog.lake =
org.apache.iceberg.spark.SparkCatalog

spark.sql.catalog.lake.type = glue

spark.sql.catalog.lake.warehouse =
s3://regdata-engine-storage/warehouse/

spark.sql.catalog.lake.io-impl =
org.apache.iceberg.aws.s3.S3FileIO
```

The actual application configuration also includes the required AWS
region and other Spark settings.

### Explanation of Important Settings

**Iceberg Spark Extensions**

``` text
IcebergSparkSessionExtensions
```

Enables Iceberg-specific Spark SQL functionality, including supported
table operations such as MERGE.

**SparkCatalog**

``` text
org.apache.iceberg.spark.SparkCatalog
```

Connects Spark SQL to the Iceberg catalog implementation.

**Catalog Type**

``` text
glue
```

Specifies that AWS Glue is being used as the catalog backend.

**Warehouse**

``` text
s3://regdata-engine-storage/warehouse/
```

Specifies the S3 location where Iceberg tables are stored.

**S3FileIO**

``` text
org.apache.iceberg.aws.s3.S3FileIO
```

Provides Iceberg's integration for reading and writing data and metadata
files using Amazon S3.

## 9.4 Creating the Iceberg Namespace

The application initializes the Iceberg namespace:

``` text
lake.regdata
```

The `lake` portion refers to the configured catalog.

The `regdata` portion refers to the database or namespace.

The namespace organizes the project's Iceberg tables.

## 9.5 Creating the Four Iceberg Tables

The application creates the following tables:

``` text
lake.regdata.raw_transactions
```

``` text
lake.regdata.clean_transactions
```

``` text
lake.regdata.quarantine_transactions
```

``` text
lake.regdata.batch_metrics
```

The table schemas are defined in the application and created through the
Iceberg writer module.

The tables serve separate purposes:

-   Raw transactions preserve the original incoming messages.
-   Clean transactions store normalized and validated records.
-   Quarantine transactions store rejected records and validation
    errors.
-   Batch metrics store processing and reconciliation statistics.

## 9.6 How Iceberg Stores Data

When Spark writes records to an Iceberg table:

1.  Spark prepares the DataFrame.
2.  Iceberg manages the table write operation.
3.  Data files are written in Parquet format to S3.
4.  Iceberg creates or updates its metadata and manifest information.
5.  The table's current metadata reference is committed through the
    catalog.

The Glue catalog is used to discover the table, while Iceberg metadata
identifies the files belonging to its current state.

This is why we can see both the table definitions in Glue and the actual
data files in S3.

# 10. Deploying the Spark Application

After configuring the infrastructure and Iceberg integration, the
transaction-processing application was deployed on the Spark Master EC2
instance.

## 10.1 Application Directory

The application was organized into the following structure:

``` text
regdata-engine/
│
├── config/
│   ├── __init__.py
│   └── spark_config.py
│
├── processing/
│   ├── __init__.py
│   ├── schemas.py
│   ├── transformations.py
│   ├── validation.py
│   ├── compliance.py
│   ├── iceberg_writer.py
│   └── transaction_processor.py
│
├── main.py
└── README.md
```

## 10.2 Packaging Python Modules

The application modules were packaged using:

``` bash
zip -r regdata_app.zip config processing
```

The resulting ZIP archive was used to distribute the application modules
to the Spark executors.

The main entry point remained `main.py`.

## 10.3 Submitting the Application

The application was submitted using `spark-submit`.

The command used was:

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

### Important Configuration Details

-   `--master` identifies the Spark Master.
-   `--deploy-mode client` runs the application driver on the submitting
    EC2 instance.
-   `--py-files` distributes the application modules.
-   `--packages` supplies Kafka and Iceberg dependencies.
-   `spark.driver.host` specifies the driver's advertised network
    address.
-   `spark.driver.port` and `spark.blockManager.port` configure
    communication ports.
-   `nohup` and `&` allow the application to continue running after the
    terminal session closes.
-   `spark_job.log` stores application output and error messages.

The driver and executor memory and core settings represent the resource
allocation requested for the application.

# 11. Verifying the Complete Infrastructure

After completing the setup, the infrastructure was verified through the
following checks.

## 11.1 Verify Spark Master

On the Spark Master EC2 instance:

``` bash
spark-submit --version
```

Expected Spark version:

``` text
3.5.9
```

Check the Spark Master web interface on port 8080.

## 11.2 Verify Spark Workers

Open the Spark Master dashboard and check that both Worker instances are
registered and ALIVE.

## 11.3 Verify Kafka--Spark Integration

Start the Python transaction generator and verify that Spark receives
messages from the Kafka topic.

## 11.4 Verify Application Execution

On the Spark Master EC2 instance:

``` bash
tail -f spark_job.log
```

This displays the application's latest log output.

To check whether the submission process is running:

``` bash
ps -ef | grep '[s]park-submit'
```

## 11.5 Verify S3 Storage

Open the S3 bucket:

``` text
regdata-engine-storage
```

Navigate to the warehouse prefix and inspect the table directories.

Verify that the application has created the expected table data and
metadata files.

## 11.6 Verify Glue Tables

Open AWS Glue Data Catalog and navigate to the `regdata` database.

Verify that the four Iceberg tables are visible:

-   raw_transactions
-   clean_transactions
-   quarantine_transactions
-   batch_metrics

Inspect the schemas to confirm that the table definitions have been
registered.

# 12. Final Infrastructure Status

The following infrastructure and integration milestones have been
completed.

  Task                                             Status
  ------------------------------------------------ -----------
  AWS EC2 infrastructure creation                  Completed
  Kafka EC2 deployment                             Completed
  Spark Master EC2 deployment                      Completed
  Spark Worker EC2 deployment                      Completed
  Java and Python setup                            Completed
  Spark 3.5.9 installation                         Completed
  Spark version mismatch resolution                Completed
  Spark Master and Worker connection               Completed
  Spark dashboard verification                     Completed
  Kafka--Spark connectivity                        Working
  S3 bucket creation and configuration             Completed
  IAM role configuration                           Completed
  Glue Data Catalog setup                          Completed
  Iceberg dependencies and catalog configuration   Completed
  Iceberg namespace and table creation             Verified
  Spark application deployment                     Completed
  S3 Parquet writes                                Observed
  Glue table schema registration                   Observed

# 13. Important Operational Considerations

## 13.1 Stop EC2 Instances When Not in Use

EC2 instances can incur charges while running.

Since this is a demonstration and academic project, stop the instances
when they are not required.

Before stopping them:

-   Confirm that the application is no longer needed.
-   Save relevant logs.
-   Make sure any required data has been committed.
-   Avoid deleting the S3 bucket or Glue catalog resources
    unintentionally.

Stopping an EC2 instance does not automatically delete its EBS volumes
or all associated AWS resources. Review storage, public IPv4 address,
and other billable resources separately.

## 13.2 Preserve the Streaming Checkpoint

The Spark application uses a checkpoint directory to maintain streaming
progress.

Do not delete or recreate the checkpoint directory casually.

If a new checkpoint is used, Spark may treat the query as a new
streaming application and its starting-offset behavior may differ.

## 13.3 Keep Spark Versions Consistent

The Spark Master and all Worker nodes should use compatible Spark
versions.

For this project, Spark 3.5.9 was selected across all three instances.

## 13.4 Secure AWS Permissions

The EC2 IAM role should contain only the permissions required by the
project.

Avoid storing long-term AWS access keys in application files or Git
repositories.

Keep the S3 bucket private and restrict access to the Glue catalog and
EC2 resources.

# 14. Conclusion

The infrastructure setup established the distributed computing and
cloud-storage foundation required by RegData Engine.

Four EC2 instances were configured to support Kafka and the Spark
Standalone cluster. The Spark Master and two Worker nodes were
configured with Spark 3.5.9, Java 17, and the required Python
environment.

Kafka was deployed separately and connected to Spark so that transaction
events could be consumed through Structured Streaming.

On the AWS side, an S3 bucket was created for Iceberg storage, an IAM
role was configured for EC2 access, and AWS Glue was selected as the
metadata catalog.

Apache Iceberg was integrated with Spark using its Spark runtime and AWS
dependencies. The application was configured to use Glue as the catalog
and S3 as the warehouse. Four Iceberg tables were created and the
application successfully wrote Parquet data to S3, with their schemas
visible in Glue.

**The completed infrastructure provides the foundation for a distributed
financial transaction-processing pipeline, with Kafka handling
ingestion, Spark handling computation, Iceberg managing analytical
tables, Glue maintaining catalog metadata, and S3 providing persistent
storage.**
