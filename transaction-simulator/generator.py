
import argparse
import json
import random
import time
import uuid
from collections import Counter
from datetime import datetime, timezone

from faker import Faker # type: ignore


fake = Faker()

# ============================================================
# 1. SCHEMA CONFIGURATION
# ============================================================

SCHEMA_FIELDS = [
    "event_id",
    "transaction_id",
    "account_id",
    "customer_name",
    "kyc_id",
    "counterparty_account_id",
    "counterparty_country",
    "amount",
    "currency",
    "transaction_type",
    "direction",
    "source",
    "timestamp",
    "status",
    "merchant_id",
    "country",
    "schema_version",
]

COUNTRIES = ["IN", "AE", "US", "GB", "DE", "SG"]
CURRENCIES = ["INR", "USD", "EUR", "GBP"]

TRANSACTION_TYPES = [
    "UPI",
    "CARD",
    "BANK_TRANSFER",
    "PAYMENT",
]

DIRECTIONS = ["DEBIT", "CREDIT"]

SOURCES = [
    "MOBILE_APP",
    "WEB_APP",
    "PAYMENT_GATEWAY",
]

STATUSES = [
    "SUCCESS",
    "FAILED",
    "PENDING",
]

# ============================================================
# 2. DATA GENERATION FUNCTIONS
# ============================================================

def generate_pan():
    """Generate a fake PAN-like identifier for testing."""
    letters = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5))
    digits = "".join(random.choices("0123456789", k=4))
    final_letter = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    return letters + digits + final_letter


def generate_customer_name():
    """Generate customer names in different formats."""

    first_name = fake.first_name()
    last_name = fake.last_name()

    name_format = random.choice([1, 2, 3])

    if name_format == 1:
        return f"{first_name} {last_name}"

    elif name_format == 2:
        return f"{last_name}_{first_name}".upper()

    else:
        return f"{first_name[0]}. {last_name}"


def generate_record():
    """Generate one synthetic financial transaction."""

    return {
        "event_id": f"EVT-{uuid.uuid4().hex[:8]}",

        "transaction_id": f"TXN-{uuid.uuid4().hex[:12]}",

        "account_id": f"ACC-{random.randint(1000, 9999)}",

        "customer_name": generate_customer_name(),

        "kyc_id": generate_pan(),

        "counterparty_account_id": f"ACC-{random.randint(1000, 9999)}",

        "counterparty_country": random.choice(COUNTRIES),

        "amount": round(random.uniform(100, 150000), 2),

        "currency": random.choice(CURRENCIES),

        "transaction_type": random.choice(TRANSACTION_TYPES),

        "direction": random.choice(DIRECTIONS),

        "source": random.choice(SOURCES),

        "timestamp": datetime.now(timezone.utc).isoformat(),

        "status": random.choice(STATUSES),

        "merchant_id": f"MER-{random.randint(100, 999)}",

        "country": random.choice(COUNTRIES),

        "schema_version": random.choice([1, 2]),
    }


# ============================================================
# 3. DATA QUALITY FLAW CONFIGURATION
# ============================================================

FLAW_TYPES = [
    "missing_account",
    "missing_kyc",
    "invalid_kyc",
    "missing_merchant",
    "invalid_timestamp",
    "negative_amount",
    "invalid_currency",
    "invalid_direction",
    "missing_counterparty",
    "duplicate_event_id",
]


def inject_flaw(record, flaw_type, existing_event_ids):
    """Inject one intentional data-quality problem."""

    if flaw_type == "missing_account":
        record["account_id"] = None

    elif flaw_type == "missing_kyc":
        record["kyc_id"] = None

    elif flaw_type == "invalid_kyc":
        record["kyc_id"] = "INVALID-KYC-123"

    elif flaw_type == "missing_merchant":
        record["merchant_id"] = None

    elif flaw_type == "invalid_timestamp":
        record["timestamp"] = "INVALID-TIMESTAMP"

    elif flaw_type == "negative_amount":
        record["amount"] = -abs(record["amount"])

    elif flaw_type == "invalid_currency":
        record["currency"] = "INVALID-CURRENCY"

    elif flaw_type == "invalid_direction":
        record["direction"] = "UNKNOWN"

    elif flaw_type == "missing_counterparty":
        record["counterparty_account_id"] = None

    elif flaw_type == "duplicate_event_id":
        if existing_event_ids:
            record["event_id"] = random.choice(existing_event_ids)
        else:
            record["event_id"] = "EVT-DUPLICATE-001"

    return record


# ============================================================
# 4. CONTINUOUS TRANSACTION GENERATOR
# ============================================================

def generate_continuously(
    output_file,
    min_rate=30,
    max_rate=40,
    flawed_ratio=0.15
):
    """
    Continuously generate synthetic transactions.

    Generates a random number of records between min_rate
    and max_rate in each one-second cycle.

    Runs until the user presses Ctrl+C.
    """

    total_records = 0
    total_flawed = 0
    total_clean = 0

    issue_counts = Counter()
    existing_event_ids = []

    start_time = time.perf_counter()

    print("\n" + "=" * 60)
    print("       REGDATA ENGINE - TRANSACTION SIMULATOR")
    print("=" * 60)

    print(f"Minimum generation rate : {min_rate} records/sec")
    print(f"Maximum generation rate : {max_rate} records/sec")
    print(f"Flawed record ratio     : {flawed_ratio * 100:.1f}%")
    print(f"Output file             : {output_file}")

    print("\nSimulator started successfully.")
    print("Press Ctrl+C to stop generation.")
    print("-" * 60)

    try:

        # Append mode preserves previously generated records.
        with open(
            output_file,
            "a",
            encoding="utf-8",
            buffering=1
        ) as file:

            while True:

                cycle_start = time.perf_counter()

                # Select target records for this one-second cycle.
                target_rate = random.randint(min_rate, max_rate)

                cycle_flawed = 0
                cycle_clean = 0

                for _ in range(target_rate):

                    record = generate_record()

                    # Randomly inject data-quality flaws.
                    if random.random() < flawed_ratio:

                        flaw_type = random.choice(FLAW_TYPES)

                        record = inject_flaw(
                            record,
                            flaw_type,
                            existing_event_ids
                        )

                        total_flawed += 1
                        cycle_flawed += 1
                        issue_counts[flaw_type] += 1

                    else:
                        total_clean += 1
                        cycle_clean += 1

                    # Write one transaction as one JSONL line.
                    file.write(json.dumps(record) + "\n")

                    # Track event IDs for duplicate injection.
                    existing_event_ids.append(record["event_id"])

                    total_records += 1

                # Flush data so generated records are visible on disk.
                file.flush()

                # Maintain approximately one-second generation cycles.
                elapsed = time.perf_counter() - cycle_start

                if elapsed < 1.0:
                    time.sleep(1.0 - elapsed)

                cycle_duration = time.perf_counter() - cycle_start
                actual_rate = target_rate / cycle_duration

                elapsed_total = time.perf_counter() - start_time

                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] "
                    f"Generated: {target_rate:2d} | "
                    f"Cycle rate: {actual_rate:5.2f} records/sec | "
                    f"Clean: {cycle_clean:2d} | "
                    f"Flawed: {cycle_flawed:2d} | "
                    f"Total: {total_records}"
                )

    except KeyboardInterrupt:

        duration = time.perf_counter() - start_time

        print("\n\n" + "=" * 60)
        print("          GENERATION STOPPED MANUALLY")
        print("=" * 60)

        print(f"Total records generated : {total_records}")
        print(f"Clean records           : {total_clean}")
        print(f"Flawed records          : {total_flawed}")

        print(f"Execution time          : {duration:.2f} seconds")

        if duration > 0:
            print(
                f"Average generation rate : "
                f"{total_records / duration:.2f} records/sec"
            )

        print("\nData Quality Issues:")

        if issue_counts:
            for issue, count in issue_counts.items():
                print(f"{issue:25}: {count}")
        else:
            print("No intentional flaws generated.")

        print(f"\nOutput file: {output_file}")
        print("=" * 60)


# ============================================================
# 5. MAIN EXECUTION
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Continuous RegData Engine transaction simulator"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="generated_transactions.jsonl",
        help="Output JSONL file"
    )

    parser.add_argument(
        "--min-rate",
        type=int,
        default=30,
        help="Minimum records generated per second"
    )

    parser.add_argument(
        "--max-rate",
        type=int,
        default=40,
        help="Maximum records generated per second"
    )

    parser.add_argument(
        "--flawed-ratio",
        type=float,
        default=0.15,
        help="Percentage of intentionally flawed records"
    )

    args = parser.parse_args()

    if args.min_rate <= 0:
        parser.error("--min-rate must be greater than zero")

    if args.max_rate < args.min_rate:
        parser.error("--max-rate must be greater than or equal to --min-rate")

    if not 0 <= args.flawed_ratio <= 1:
        parser.error("--flawed-ratio must be between 0 and 1")

    generate_continuously(
        output_file=args.output,
        min_rate=args.min_rate,
        max_rate=args.max_rate,
        flawed_ratio=args.flawed_ratio
    )
