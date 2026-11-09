# RegData Engine — Phase 2 Kafka Implementation Log

**Date:** 2026-10-31

---

## Overview

Phase 2 connects Layer 1 (transaction generator on your laptop) to Apache Kafka running on an AWS EC2 server. Kafka acts as a message broker — your laptop sends transactions into it, and Spark (Layer 3) will read them from it.

**Architecture we built today:**

```
Your Laptop (Windows)
  └── generator.py
        └── sends transactions via port 9092
              └── EC2 Server (43.205.228.22) — Mumbai (ap-south-1)
                    └── Kafka Broker (Docker, KRaft mode)
                          ├── transactions topic (3 partitions)
                          ├── customers topic (3 partitions)
                          ├── kyc_events topic (3 partitions)
                          └── transactions.dlq topic (1 partition)
                    └── Kafka UI (localhost:8080 via SSH tunnel)
```

**What KRaft mode means:** Kafka runs without ZooKeeper (an older dependency). It manages itself. Simpler and lighter — perfect for a single-broker setup.

---

## Phase 1 — AWS Setup

**Goal:** Get an EC2 server ready to run Kafka.

### Key Pair
- Used existing key pair: `RegData-key`
- File location on laptop: `D:\sem 7\RegData_engine\RegData-key.pem`
- This file is your password to SSH into the server. Never share it.

### Security Group: `regdata-kafka-sg`
- ID: `sg-0616a55dfffd4610a`

| Port | Used by | Source |
| --- | --- | --- |
| 22 | SSH (your laptop controls the server) | Your IP (My IP) |
| 9092 | Your laptop → Kafka (send transactions) | Your IP (My IP) |
| 9093 | Spark → Kafka (read transactions) | Spark security group |

> **Important:** Port 9092 and 9093 are swapped from the original plan because we couldn't edit the security group sources. We adapted Kafka config to match.

### EC2 Instance: `regdata-kafka`
- Instance ID: `i-0a3de847a656a8d24`
- Type: `t3.micro` (1GB RAM — tight but works for demo)
- Public IP: `43.205.228.22`
- Private IP: `10.0.1.80`
- Region: Mumbai (`ap-south-1`)
- OS: Ubuntu 24.04 LTS
- Docker: pre-installed

### How to SSH into the server
```powershell
ssh -i "D:\sem 7\RegData_engine\RegData-key.pem" ubuntu@43.205.228.22
```

> **Note:** If SSH times out, your IP has changed. Go to EC2 → Security Groups → `regdata-kafka-sg` → Edit inbound rules → set port 22 and 9092 source to "My IP".

---

## Phase 2 — Kafka Running

**Goal:** Start Kafka inside Docker on the EC2 server.

### Files created (stored at `D:\sem 7\RegData_engine\kafka-setup\`)

| File | Purpose |
| --- | --- |
| `docker-compose.yml` | Tells Docker how to run Kafka (ports, memory, listeners) |
| `start.sh` | Auto-detects server IPs and starts Kafka |
| `test_connection.py` | Tests if laptop can talk to Kafka |

### Upload files to EC2
```powershell
scp -i "D:\sem 7\RegData_engine\RegData-key.pem" -r "D:\sem 7\RegData_engine\kafka-setup" ubuntu@43.205.228.22:~/
```

### Start Kafka on EC2
```bash
cd ~/kafka-setup
sudo rm -rf ./data
mkdir -p ./data
sudo chown -R 1000:1000 ./data
docker compose up -d
```

### Verify Kafka started
```bash
docker logs kafka --tail 20
```
Look for: `Kafka Server started`

### Two listeners explained

| Listener | Port | Used by | Why |
| --- | --- | --- | --- |
| EXTERNAL | 9092 | Your laptop | Sends transactions from outside AWS |
| INTERNAL | 9093 | Spark (inside AWS) | Reads transactions from inside AWS |

> The `docker-compose.yml` has both IPs hardcoded:
> - `INTERNAL://10.0.1.80:9093` (private IP)
> - `EXTERNAL://43.205.228.22:9092` (public IP)

---

## Phase 3 — Topics Created

**Goal:** Create the Kafka "mailboxes" where transactions will be stored.

### Create all 4 topics
```bash
docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9093 --create --topic transactions --partitions 3 --replication-factor 1

sleep 5 && docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9093 --create --topic customers --partitions 3 --replication-factor 1

sleep 5 && docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9093 --create --topic kyc_events --partitions 3 --replication-factor 1

sleep 5 && docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9093 --create --topic transactions.dlq --partitions 1 --replication-factor 1 --config retention.ms=1209600000
```

### Verify topics exist
```bash
docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9093 --list
```
Expected output:
```
customers
kyc_events
transactions
transactions.dlq
```

### Topics explained

| Topic | Partitions | Retention | Purpose |
| --- | --- | --- | --- |
| `transactions` | 3 | 7 days | Every financial transaction from generator.py |
| `customers` | 3 | 7 days | Customer profile data |
| `kyc_events` | 3 | 7 days | KYC verification events |
| `transactions.dlq` | 1 | 14 days | Broken/invalid messages (Dead Letter Queue) |

### Check message count per partition
```bash
docker exec kafka /opt/kafka/bin/kafka-get-offsets.sh --bootstrap-server localhost:9093 --topic transactions
```

### Read messages from a topic
```bash
docker exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9093 \
  --topic transactions \
  --partition 0 \
  --offset earliest \
  --max-messages 5
```
> Always use `--partition 0 --offset earliest` instead of `--from-beginning` to avoid group coordinator issues.

---

## Phase 4 — Layer 1 Connects to Kafka

**Goal:** Modify `generator.py` so it sends every transaction to Kafka in addition to writing to the file.

### What changed in `generator.py`
- Added `confluent-kafka` import
- Added `make_kafka_producer()` function — creates the Kafka connection
- Added `send_to_kafka()` function — wraps each record in an envelope and sends it
- Added `--kafka` command line argument
- Each generated record now goes to both the JSONL file AND Kafka

### Message envelope format
Every message sent to Kafka looks like this:
```json
{
  "schema_version": 1,
  "event_id": "EVT-f78ed54e",
  "event_type": "transaction",
  "source_system": "layer1_generator",
  "produced_at": "2026-10-31T08:43:42Z",
  "payload": {
    "transaction_id": "TXN-caaf56eba1fd",
    "account_id": "ACC-4531",
    "amount": 129914.81,
    "...all 17 fields..."
  }
}
```

### How to run the generator with Kafka
```powershell
cd "D:\sem 7\RegData_engine\transaction-simulator"
python generator.py --kafka 43.205.228.22:9092 --min-rate 5 --max-rate 5
```
- `--kafka 43.205.228.22:9092` — connects to Kafka on EC2
- `--min-rate 5 --max-rate 5` — 5 records/sec (use 30-40 for production)

### Test connection from laptop
```powershell
cd "D:\sem 7\RegData_engine\kafka-setup"
python test_connection.py 43.205.228.22
```
Expected output: `PASS - Kafka connection is working!`

### Install required library first
```powershell
pip install confluent-kafka
```

---

## Phase 5 — Kafka UI Dashboard

**Goal:** View Kafka topics, messages and stats through a browser dashboard.

### What is Kafka UI
A web dashboard running on the EC2 server that shows all topics, message counts, partitions, and live data. We access it safely through an SSH tunnel — port 8080 is never opened publicly.

### Start the SSH tunnel (run every session)
Open a dedicated PowerShell window and run:
```powershell
ssh -i "D:\sem 7\RegData_engine\RegData-key.pem" -L 8080:localhost:8080 -o ServerAliveInterval=60 ubuntu@43.205.228.22 -N
```
- This window will appear frozen — that is normal, the tunnel is active
- `-o ServerAliveInterval=60` keeps the tunnel alive and prevents disconnection
- Do NOT close this window while using the dashboard

### Open the dashboard
While the tunnel window is running, open your browser and go to:
```
http://localhost:8080
```

### What you can see in Kafka UI

| Section | What it shows |
| --- | --- |
| Dashboard | Cluster status, broker count, total topics |
| Topics | List of all topics, message count, partition count, size |
| Topics → transactions | Individual messages, which partition they are in |
| Brokers | Kafka broker health and config |

### If the dashboard shows 404 or goes offline
The SSH tunnel dropped. Close and rerun the tunnel command above.

---

## Important Config Reference

### AWS Resources

| Resource | Name | ID / Value |
| --- | --- | --- |
| EC2 Instance | regdata-kafka | i-0a3de847a656a8d24 |
| Public IP | — | 43.205.228.22 |
| Private IP | — | 10.0.1.80 |
| Security Group | regdata-kafka-sg | sg-0616a55dfffd4610a |
| Spark Security Group | regdata-spark-sg | sg-00fc7a95deed14235 |
| Key Pair | RegData-key | D:\sem 7\RegData_engine\RegData-key.pem |
| VPC | default | vpc-089e13544ffe4655c |
| Region | Mumbai | ap-south-1 |
| Account ID | — | 7776163183407 |

### Port Reference

| Port | Listener | Used by | Direction |
| --- | --- | --- | --- |
| 22 | SSH | Your laptop | Laptop → EC2 |
| 9092 | EXTERNAL | Your laptop | Laptop → Kafka |
| 9093 | INTERNAL | Spark machines | Spark → Kafka |
| 8080 | Kafka UI | Browser (via SSH tunnel only) | Laptop → Dashboard |

### Important Note on Ports
The original plan used port 9094 for the laptop. We changed to **9092** because the security group already had 9092 open for our IP. Port numbers in Kafka config and security group must always match.

### Kafka docker-compose.yml location
- On laptop: `D:\sem 7\RegData_engine\kafka-setup\docker-compose.yml`
- On EC2: `~/kafka-setup/docker-compose.yml`

---

## Daily Routine

### Every time you START a work session

**Step 1 — Start the EC2 instance** (if it is stopped)
- Go to AWS Console → EC2 → Instances → select `regdata-kafka` → Instance state → Start
- Wait until status shows **Running**

**Step 2 — Check your IP hasn't changed**
```powershell
(Invoke-WebRequest -Uri "https://api.ipify.org" -UseBasicParsing).Content
```
If the IP is different from last time, update the security group:
- EC2 → Security Groups → `regdata-kafka-sg` → Edit inbound rules
- Set port 22 and port 9092 source to **My IP**

**Step 3 — SSH into the server**
```powershell
ssh -i "D:\sem 7\RegData_engine\RegData-key.pem" ubuntu@43.205.228.22
```

**Step 4 — Start Kafka** (if not already running)
```bash
cd ~/kafka-setup
docker compose up -d
```
Verify: `docker ps` should show both `kafka` and `kafka-ui` running.

**Step 5 — Recreate topics** (only if you restarted Kafka fresh with wiped data)
```bash
docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9093 --create --topic transactions --partitions 3 --replication-factor 1
sleep 5 && docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9093 --create --topic customers --partitions 3 --replication-factor 1
sleep 5 && docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9093 --create --topic kyc_events --partitions 3 --replication-factor 1
sleep 5 && docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9093 --create --topic transactions.dlq --partitions 1 --replication-factor 1 --config retention.ms=1209600000
```

**Step 6 — Open Kafka UI** (open a new PowerShell window)
```powershell
ssh -i "D:\sem 7\RegData_engine\RegData-key.pem" -L 8080:localhost:8080 -o ServerAliveInterval=60 ubuntu@43.205.228.22 -N
```
Then open `http://localhost:8080` in your browser.

**Step 7 — Run the generator**
```powershell
cd "D:\sem 7\RegData_engine\transaction-simulator"
python generator.py --kafka 43.205.228.22:9092 --min-rate 30 --max-rate 40
```

---

### Every time you END a work session
1. Press **Ctrl+C** in the generator window to stop it
2. Close the SSH tunnel window
3. Go to AWS Console → EC2 → select `regdata-kafka` → Instance state → **Stop**

> Stopping the instance saves your AWS credits. Data on the disk is preserved.

---

## Phase 6 — Spark Reads from Kafka

**Goal:** Connect Spark Structured Streaming (Layer 3) to Kafka (Layer 2) so Spark can read live transactions.

### Spark EC2 Details

| Resource | Value |
| --- | --- |
| Master Public IP | `13.233.24.66` |
| Master Private IP | `10.0.1.27` |
| Worker 1 Public IP | `15.206.92.231` |
| Worker 2 Public IP | `13.206.147.43` |
| Instance type | t3.small |
| OS | Ubuntu 24.04 LTS |
| Key Pair | RegData-key (same as Kafka) |

### How to SSH into Spark master
```powershell
ssh -i "D:\sem 7\RegData_engine\RegData-key.pem" ubuntu@13.233.24.66
```

### What was installed on Spark EC2

| Software | Version | Location |
| --- | --- | --- |
| Java (OpenJDK) | 17.0.20.1 | pre-installed |
| Python | 3.12.3 | pre-installed |
| Spark | 3.5.3 | `~/spark-3.5.3-bin-hadoop3/` |
| spark-sql-kafka connector | 3.5.3 | `~/spark-3.5.3-bin-hadoop3/jars/` |
| kafka-clients | 3.4.1 | `~/spark-3.5.3-bin-hadoop3/jars/` |
| commons-pool2 | 2.11.1 | `~/spark-3.5.3-bin-hadoop3/jars/` |
| spark-token-provider-kafka | 3.5.3 | `~/spark-3.5.3-bin-hadoop3/jars/` |

### Spark installation commands
```bash
# Download Spark
wget -q https://archive.apache.org/dist/spark/spark-3.5.3/spark-3.5.3-bin-hadoop3.tgz

# Extract
tar -xzf spark-3.5.3-bin-hadoop3.tgz

# Set environment variables
echo 'export SPARK_HOME=~/spark-3.5.3-bin-hadoop3' >> ~/.bashrc
echo 'export PATH=$PATH:$SPARK_HOME/bin' >> ~/.bashrc
source ~/.bashrc

# Download Kafka connector JARs
wget -q https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.3/spark-sql-kafka-0-10_2.12-3.5.3.jar -P ~/spark-3.5.3-bin-hadoop3/jars/
wget -q https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.1/kafka-clients-3.4.1.jar -P ~/spark-3.5.3-bin-hadoop3/jars/
wget -q https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar -P ~/spark-3.5.3-bin-hadoop3/jars/
wget -q https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.3/spark-token-provider-kafka-0-10_2.12-3.5.3.jar -P ~/spark-3.5.3-bin-hadoop3/jars/
```

### Spark streaming job
File location on Spark EC2: `~/spark_kafka_job.py`

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, get_json_object

spark = SparkSession.builder \
    .appName("RegData-Layer3") \
    .master("local[*]") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

df = (spark.readStream
      .format("kafka")
      .option("kafka.bootstrap.servers", "10.0.1.80:9093")
      .option("subscribe", "transactions")
      .option("startingOffsets", "earliest")
      .load())

raw = df.selectExpr("CAST(value AS STRING) as raw_json")

transactions = raw.select(
    get_json_object(col("raw_json"), "$.event_id").alias("event_id"),
    get_json_object(col("raw_json"), "$.payload.transaction_id").alias("transaction_id"),
    get_json_object(col("raw_json"), "$.payload.account_id").alias("account_id"),
    get_json_object(col("raw_json"), "$.payload.amount").cast("double").alias("amount"),
    get_json_object(col("raw_json"), "$.payload.currency").alias("currency"),
    get_json_object(col("raw_json"), "$.payload.transaction_type").alias("transaction_type"),
    get_json_object(col("raw_json"), "$.payload.status").alias("status"),
)

query = (transactions.writeStream
         .format("console")
         .option("truncate", False)
         .option("numRows", 5)
         .start())

query.awaitTermination()
```

### How to run the Spark job
```bash
spark-submit spark_kafka_job.py
```

### Security group update for Spark → Kafka
Added inbound rule to `regdata-kafka-sg`:
- Port: `9092`
- Source: `sg-00fc7a95deed14235` (regdata-spark-sg)
- This allows Spark machines inside AWS to connect to Kafka

### Verified working
- Spark connects to Kafka at `10.0.1.80:9093` (private IP, INTERNAL listener)
- Batch 0 showed real transaction records from the `transactions` topic
- ~15% flawed records visible in the data (negative amounts, null fields, etc.)

### Important note on WARN messages
When Spark job runs, you will see repeated WARN messages:
```
WARN NetworkClient: Connection to node 1 (/10.0.1.80:9093) could not be established.
```
These are from Spark's AdminClient (used for metadata). The actual data reading works correctly — ignore these warnings.
