# RegData Engine — Layer 2 (Kafka Ingestion & Streaming)
## Phase-wise Implementation Plan

| Item | Value |
|---|---|
| Owner | Guru |
| Layer | 2 — Ingestion & Streaming (Apache Kafka) |
| Input | Layer 1 synthetic data generator (runs on laptop, ~40 records/sec) |
| Output | Kafka topics read by Layer 3 (Spark on EC2) |
| Cloud | AWS, **Asia Pacific (Mumbai) — ap-south-1** |
| Budget | ~80 AWS credits → keep it to **one EC2 instance**, stop it after work |

```
Your laptop                         AWS Mumbai (same VPC)
───────────                         ─────────────────────────────────────────
Layer 1 generator ──PUBLIC_IP:9094──▶ EC2: Kafka broker ──PRIVATE_IP:9092──▶ EC2: Spark (Layer 3)
(Kafka producer)     (EXTERNAL)       (Docker, KRaft)       (INTERNAL)
```

### Phase overview

```
Phase 1      Phase 2        Phase 3         Phase 4        Phase 5        Phase 6
AWS setup → Kafka running → Topics &     → Connect     → Monitoring  → Hand-off
(EC2)       (1 broker)      message format  Layer 1        & safety       to Spark
```

| Phase | Goal | Done when |
|---|---|---|
| 1 | EC2 instance ready | You can SSH in and `docker ps` works |
| 2 | Kafka running | `test_connection.py` from laptop prints PASS |
| 3 | Real topics + message format | Topics exist, format written down |
| 4 | Layer 1 sends to Kafka | 40 records/sec arrive in Kafka |
| 5 | Monitoring | Live data visible in Kafka UI |
| 6 | Spark reads Kafka | Spark reads `transactions` live |

---

## Phase 1 — AWS Setup

**Goal:** one EC2 machine ready to run Kafka.

### Steps
1. Log in to AWS with the IAM user. Set region to **Mumbai (ap-south-1)**.
2. Create a **key pair** (`regdata-kafka.pem`). Keep it safe on your laptop.
3. Create a **security group** `regdata-kafka-sg`:

   | Port | Source | Why |
   |---|---|---|
   | 22 | My IP | SSH |
   | 9094 | My IP | Laptop → Kafka |
   | 9092 | VPC CIDR / Spark security group | Spark → Kafka (add when Spark is ready) |

   ⚠️ Never open 9092 or 9094 to `0.0.0.0/0`.
4. Launch EC2:
   - AMI: **Ubuntu 24.04**
   - Type: **t3.medium** (4 GB RAM)
   - Disk: **20 GB gp3**
   - Same VPC Spark will use
5. Install Docker:
   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose-v2
   sudo usermod -aG docker ubuntu
   exit   # SSH back in
   ```

**Done when:** `ssh -i regdata-kafka.pem ubuntu@<PUBLIC_IP>` works and `docker ps` runs without error.

**Security note:** keep IAM credentials only on your machine (`aws configure`). Never paste them in chat or push them to GitHub.

---

## Phase 2 — Get Kafka Running

**Goal:** one Kafka broker (KRaft mode, no ZooKeeper) reachable from laptop and Spark.

### Files
| File | Where | Purpose |
|---|---|---|
| `docker-compose.yml` | EC2 `~/kafka/` | Kafka broker with 2 listeners, 1 GB heap, 7-day retention |
| `start.sh` | EC2 `~/kafka/` | Reads current private/public IP, starts Kafka |
| `test_connection.py` | Laptop | Sends 10 messages and reads them back |

### Two listeners (most important part)
| Listener | Port | Address | Used by |
|---|---|---|---|
| INTERNAL | 9092 | Private IP | Spark (inside VPC) |
| EXTERNAL | 9094 | Public IP | Your laptop |

If the advertised IP is wrong, the laptop connects but cannot send data.

### Steps
1. Create folder on EC2:
   ```bash
   mkdir -p ~/kafka/data
   sudo chown -R 1000:1000 ~/kafka/data
   ```
2. Copy files from laptop:
   ```bash
   scp -i regdata-kafka.pem docker-compose.yml start.sh ubuntu@<PUBLIC_IP>:~/kafka/
   ```
3. Start Kafka (on EC2):
   ```bash
   chmod +x ~/kafka/start.sh
   ~/kafka/start.sh
   docker logs kafka --tail 30     # look for "Kafka Server started"
   ```
4. Test on EC2:
   ```bash
   docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 \
     --create --topic test --partitions 3 --replication-factor 1
   docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
   ```
5. Test from laptop:
   ```bash
   pip install confluent-kafka
   python test_connection.py <PUBLIC_IP>:9094
   ```

**Done when:** laptop test prints `Sent 10/10`, `Read 10`, `PASS`.

### Troubleshooting
| Problem | Likely cause |
|---|---|
| Laptop times out | Port 9094 not open to your IP, or your home IP changed |
| Connects but sends nothing | Wrong advertised IP → re-run `start.sh` |
| Container restarts, "permission denied" | Re-run the `chown` command |
| Container exits, out of memory | Instance smaller than t3.medium |

---

## Phase 3 — Topics & Message Format

**Goal:** create the real topics and fix the message format.

### Topics
| Topic | Partitions | Key | Retention |
|---|---|---|---|
| `transactions` | 3 | `account_id` / `customer_id` | 7 days |
| `customers` | 3 | `customer_id` | 7 days |
| `kyc_events` | 3 | `customer_id` | 7 days |
| `transactions.dlq` | 1 | same as source | 14 days |

- **3 partitions** → matches 3–4 Spark machines, so they read in parallel.
- **Key = customer/account ID** → all events of one customer stay in order.
- **7-day retention** → Kafka is only the pipe; long-term storage is Iceberg (Layer 4).
- **DLQ (dead-letter queue)** → broken records go here instead of crashing the pipeline (matches NF3 in the SRD).

### Create topics
```bash
for t in transactions customers kyc_events; do
  docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 \
    --create --topic $t --partitions 3 --replication-factor 1
done
docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 \
  --create --topic transactions.dlq --partitions 1 --replication-factor 1 \
  --config retention.ms=1209600000
```

### Message format (JSON)
Every message should have these envelope fields, plus the record's own fields:

```json
{
  "schema_version": 1,
  "event_id": "uuid",
  "event_type": "transaction",
  "source_system": "layer1_generator",
  "produced_at": "2026-10-31T10:15:00Z",
  "payload": { "...fields from Layer 1..." }
}
```

- `schema_version` → handles schema drift later.
- `event_id` → helps Spark remove duplicates and helps lineage tracking.
- `source_system` → first step of data lineage.

**Done when:** topics exist and the message format is shared with the team (fill `payload` using a real Layer 1 sample record).

---

## Phase 4 — Connect Layer 1 (Producer)

**Goal:** Layer 1 generator sends every record to Kafka.

### Steps
1. Add a Kafka producer to the Layer 1 code (`confluent-kafka`).
2. Use safe settings:
   ```python
   producer = Producer({
       "bootstrap.servers": "<PUBLIC_IP>:9094",
       "acks": "all",                 # wait for broker to confirm
       "enable.idempotence": True,    # no duplicates on retry
       "linger.ms": 50,               # small batching
       "compression.type": "lz4",
   })
   ```
3. Send each record to the right topic with the right key:
   ```python
   producer.produce("transactions", key=rec["account_id"], value=json.dumps(msg), callback=on_delivery)
   producer.poll(0)
   ```
4. Call `producer.flush()` when the generator stops.
5. Keep the Kafka address in a `.env` file, not hard-coded.
6. Run a small reader on the laptop to check data is arriving.

**Done when:** generator runs for 5+ minutes at ~40 records/sec with zero delivery errors, and message count in Kafka matches what was sent.

---

## Phase 5 — Monitoring & Safety

**Goal:** see what Kafka is doing and keep costs under control.

### Steps
1. Add **Kafka UI** to `docker-compose.yml` (image `provectuslabs/kafka-ui`), port 8080 — **do not open 8080 in the security group**.
2. Open it from laptop through an SSH tunnel:
   ```bash
   ssh -i regdata-kafka.pem -L 8080:localhost:8080 ubuntu@<PUBLIC_IP>
   # then open http://localhost:8080
   ```
3. Watch: messages per topic, consumer lag, disk usage (`df -h`).
4. Daily routine:
   - **Start:** start instance → SSH → `~/kafka/start.sh` → update laptop `.env` with new public IP
   - **Stop:** stop instance from AWS console (data stays on disk)
5. Optional: attach an **Elastic IP** so the public IP stays the same.
6. Set an **AWS budget alert** (e.g. at $50) so credits don't run out by surprise.

**Done when:** live data is visible in Kafka UI and the start/stop routine is followed.

---

## Phase 6 — Hand-off to Spark (Layer 3)

**Goal:** friend's Spark machines read Kafka data live.

### Steps
1. Open port **9092** in `regdata-kafka-sg` for the Spark security group.
2. Share a short hand-off note:

   | Item | Value |
   |---|---|
   | Bootstrap server | `<PRIVATE_IP>:9092` |
   | Topics | `transactions`, `customers`, `kyc_events`, `transactions.dlq` |
   | Format | JSON envelope (Phase 3) |
   | Key | customer/account ID |
   | Partitions | 3 per topic |

3. Spark Structured Streaming read (example):
   ```python
   df = (spark.readStream.format("kafka")
         .option("kafka.bootstrap.servers", "<PRIVATE_IP>:9092")
         .option("subscribe", "transactions")
         .option("startingOffsets", "earliest")
         .load())
   ```
4. Test once from a Spark machine in the same VPC.

**Done when:** Spark reads the `transactions` topic live and record counts match.

---

## Later (Optional Upgrades)

| Upgrade | When |
|---|---|
| **Debezium CDC** | If Layer 1 starts writing into PostgreSQL |
| **3 brokers** (replication factor 3) | When fault tolerance matters (demo to investors / pilot) |
| **Schema Registry + Avro** | When message formats start changing often |
| **Amazon MSK** | Only with real funding — too costly for current credits |

---

## Cost Checklist
- [ ] Only one EC2 (t3.medium) for Kafka
- [ ] Instance stopped after every work session
- [ ] AWS budget alert set
- [ ] No MSK, no NAT Gateway
- [ ] Kafka in same region/VPC as Spark (no data transfer cost)
