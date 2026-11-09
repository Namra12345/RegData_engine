# RegData Engine — Full Pipeline Running Guide

**Date:** 2026-11-01  
**Author:** Aditya Panchal  
**Purpose:** Step-by-step guide to start and test the full pipeline (Layer 1 → Layer 2 → Layer 3)

---

## Architecture Overview

```
Your Laptop (Windows)
  └── generator.py (Layer 1)
        └── sends transactions via port 9092
              └── Kafka EC2 (43.205.228.22) — Mumbai (ap-south-1)
                    └── Apache Kafka 3.7.0 (Docker, KRaft mode)
                          ├── transactions topic (3 partitions)
                          ├── customers topic (3 partitions)
                          ├── kyc_events topic (3 partitions)
                          └── transactions.dlq topic (1 partition)
                    └── Spark EC2 (13.233.24.66) — Mumbai (ap-south-1)
                          └── Spark 3.5.3 Structured Streaming (Layer 3)
                                └── reads from transactions topic
```

---

## AWS Resources

| Resource | Value |
|----------|-------|
| Kafka EC2 Public IP | `43.205.228.22` |
| Kafka EC2 Private IP | `10.0.1.80` |
| Spark Master Public IP | `13.233.24.66` |
| Spark Master Private IP | `10.0.1.27` |
| Spark Worker 1 Public IP | `15.206.92.231` |
| Spark Worker 2 Public IP | `13.206.147.43` |
| Key Pair file | `D:\sem 7\RegData_engine\RegData-key.pem` |
| Region | Mumbai (`ap-south-1`) |
| VPC | `vpc-089e13544ffe4655c` |
| Kafka Security Group | `sg-0616a55dfffd4610a` (regdata-kafka-sg) |
| Spark Security Group | `sg-00fc7a95deed14235` (regdata-spark-sg) |

---

## Port Reference

| Port | Used by | Direction |
|------|---------|-----------|
| 22 | SSH | Laptop → EC2 |
| 9092 | Kafka EXTERNAL listener | Laptop → Kafka |
| 9093 | Kafka INTERNAL listener | Spark → Kafka |

---

## Prerequisites (One-time setup — already done)

- [x] Kafka EC2 running with Docker installed
- [x] Spark EC2 running with Spark 3.5.3 installed
- [x] Kafka connector JARs installed on Spark EC2
- [x] Security group rules configured
- [x] `generator.py` updated with Kafka support
- [x] `spark_kafka_job.py` created on Spark EC2

---

## STEP 1 — Start Kafka EC2

1. Go to **AWS Console → EC2 → Instances**
2. Select `regdata-kafka` → **Instance state → Start**
3. Wait until status shows **Running**

> If EC2 was stopped, the public IP may have changed. Check it from the AWS console under "Public IPv4 address".

---

## STEP 2 — Check Your Laptop IP

Your IP changes every session. Run this in PowerShell:

```powershell
(Invoke-WebRequest -Uri "https://api.ipify.org" -UseBasicParsing).Content
```

If the IP is different from last time:
- Go to **EC2 → Security Groups → regdata-kafka-sg → Edit inbound rules**
- Update port **22** and port **9092** source to **My IP**
- Save rules

---

## STEP 3 — SSH into Kafka EC2

```powershell
ssh -i "D:\sem 7\RegData_engine\RegData-key.pem" ubuntu@43.205.228.22
```

> If you get "Permission denied" error on the .pem file, run:
> ```powershell
> icacls "D:\sem 7\RegData_engine\RegData-key.pem" /inheritance:r
> icacls "D:\sem 7\RegData_engine\RegData-key.pem" /grant:r "$($env:USERNAME):(R)"
> ```

---

## STEP 4 — Start Kafka

```bash
cd ~/kafka-setup
docker compose up -d
```

Wait 35 seconds, then verify Kafka and topics are ready:

```bash
sleep 35 && docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9093 --list
```

Expected output:
```
customers
kyc_events
transactions
transactions.dlq
```

> Topics are created automatically by the `topic-init` container. No manual steps needed.

If topics don't appear, run manually:
```bash
~/kafka-setup/recreate_topics.sh
```

---

## STEP 5 — Start the Transaction Generator (Laptop)

Open a **new PowerShell window** on your laptop:

```powershell
cd "D:\sem 7\RegData_engine\transaction-simulator"
python generator.py --kafka 43.205.228.22:9092 --min-rate 30 --max-rate 40
```

You should see output like:
```
[08:43:42] Generated: 35 | Cycle rate: 35.00 records/sec | Clean: 30 | Flawed: 5 | Total: 35
```

> Use `--min-rate 5 --max-rate 5` for slow testing, `--min-rate 30 --max-rate 40` for production.

---

## STEP 6 — Verify Messages Reaching Kafka

On the Kafka EC2, run:

```bash
docker exec kafka /opt/kafka/bin/kafka-get-offsets.sh --bootstrap-server localhost:9093 --topic transactions
```

Expected output (numbers should increase each time you run it):
```
transactions:0:82
transactions:1:86
transactions:2:92
```

> Three lines = three partitions. Non-zero and increasing numbers = messages are flowing.

---

## STEP 7 — Start Spark Streaming Job

Open a **new PowerShell window** and SSH into Spark master:

```powershell
ssh -i "D:\sem 7\RegData_engine\RegData-key.pem" ubuntu@13.233.24.66
```

Then run the Spark job using the full cluster command:

```bash
cd ~/regdata-engine
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
echo "Spark job started"
```

**What this command does:**

| Option | Purpose |
|--------|---------|
| `nohup ... &` | Runs job in background — keeps running even if SSH disconnects |
| `--master spark://10.0.1.27:7077` | Uses full Spark cluster (master + 2 workers) |
| `--driver-memory 512m` | Memory allocated to Spark driver |
| `--executor-memory 512m` | Memory allocated to each executor |
| `--total-executor-cores 2` | Uses 2 cores across all workers |
| `--packages` | Auto-downloads Kafka and Iceberg JARs (version 1.9.2) |
| `--py-files regdata_app.zip` | Includes all processing Python files |
| `> spark_job.log 2>&1` | Saves all output to log file |

Monitor the log to see batch progress:

```bash
tail -f ~/regdata-engine/spark_job.log
```

Wait 2-3 minutes for the first batch. You should see:

```
========== BATCH 0 ==========
Incoming records    : 600
Clean records       : 510
Quarantined records : 90
Reconciliation      : PASSED
==============================
```

Press **Ctrl+C** to stop watching the log — the job keeps running in background.

Check if job is still running:

```bash
ps aux | grep spark-submit
```

---

To kill the Process we have to used below command
kill process_id

## STEP 8 — End of Session

1. Press **Ctrl+C** in the generator window to stop it
2. Stop the Spark job: `kill $(ps aux | grep spark-submit | grep -v grep | awk '{print $2}')`
3. On Kafka EC2: `docker compose down`
4. Go to AWS Console → EC2 → stop both `regdata-kafka` and Spark instances to save credits

---

## Troubleshooting

### SSH connection timed out
**Cause:** Your laptop IP changed.  
**Fix:** Update port 22 source in `regdata-kafka-sg` security group to "My IP".

### Generator shows REQTMOUT errors
**Cause:** Kafka EC2 is not running or IP changed.  
**Fix:** Start the EC2 instance and verify its public IP matches `43.205.228.22`.

### Topics missing after Kafka restart
**Cause:** Data folder wiped on restart (t3.micro memory issue).  
**Fix:** Run `~/kafka-setup/recreate_topics.sh`

### Kafka crashes repeatedly (OOM)
**Cause:** t3.micro only has 1GB RAM — not enough for Kafka + Kafka-UI together.  
**Fix:** Kafka-UI is disabled. Kafka runs alone with `-Xmx256m` heap. If still crashing, restart with:
```bash
docker compose down && sudo rm -rf ./data && mkdir -p ./data && sudo chown -R 1000:1000 ./data && docker compose up -d
```

### Spark shows "ClassNotFoundException: KafkaConfigUpdater"
**Cause:** Missing Kafka connector JAR.  
**Fix:** Download the missing JAR:
```bash
wget -q https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.3/spark-token-provider-kafka-0-10_2.12-3.5.3.jar -P ~/spark-3.5.3-bin-hadoop3/jars/
```

### Spark reads 0 messages
**Cause:** Generator is not running or topics are empty.  
**Fix:** Start the generator first, wait 30 seconds, then start Spark.

### kafka-get-offsets returns empty
**Cause:** Topics exist but no messages yet.  
**Fix:** Start the generator and wait 30 seconds.

---

## Key Files

| File | Location | Purpose |
|------|----------|---------|
| `generator.py` | `D:\sem 7\RegData_engine\transaction-simulator\` | Transaction generator (Layer 1) |
| `docker-compose.yml` | `~/kafka-setup/` on Kafka EC2 | Kafka Docker config |
| `recreate_topics.sh` | `~/kafka-setup/` on Kafka EC2 | Manually recreate topics if needed |
| `init-topics.sh` | `~/kafka-setup/` on Kafka EC2 | Auto-runs on startup to create topics |
| `spark_kafka_job.py` | `~/` on Spark EC2 | Spark streaming job (Layer 3) |
| `RegData-key.pem` | `D:\sem 7\RegData_engine\` | SSH key for all EC2 instances |

---

## Important Notes

- **Always start Kafka before running the generator** — if Kafka is not ready, messages are lost
- **t3.micro memory is tight** — never run Kafka-UI alongside Kafka on this machine
- **Stop EC2 instances after every session** — saves AWS credits
- **Topics persist as long as Kafka data folder is not wiped** — do not run `sudo rm -rf ./data` unless Kafka is broken
- **Spark connects via private IP `10.0.1.80:9093`** — this only works from inside AWS VPC
- **Laptop connects via public IP `43.205.228.22:9092`** — this only works from outside AWS
