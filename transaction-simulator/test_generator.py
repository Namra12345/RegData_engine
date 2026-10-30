
import json
import time
import random
from collections import Counter
from generator import generate_transaction


# -------------------------------
# CONFIGURATION
# -------------------------------

DURATION_SECONDS = 30

MIN_RECORDS_PER_SECOND = 30
MAX_RECORDS_PER_SECOND = 40

OUTPUT_FILE = "generated_transactions.jsonl"


# -------------------------------
# STATISTICS
# -------------------------------

total_records = 0
clean_records = 0
flawed_records = 0

issue_counts = Counter()
actual_duplicate_ids = Counter()

start_time = time.monotonic()


# -------------------------------
# GENERATION
# -------------------------------

print("\nStarting Synthetic Transaction Generator")
print("-----------------------------------------")

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:

    try:
        for second in range(DURATION_SECONDS):

            target_count = random.randint(
                MIN_RECORDS_PER_SECOND,
                MAX_RECORDS_PER_SECOND
            )

            second_start = time.monotonic()

            for _ in range(target_count):

                transaction, is_clean, issue = generate_transaction()

                # Save transaction as JSONL
                file.write(json.dumps(transaction) + "\n")

                total_records += 1
                actual_duplicate_ids[transaction["transaction_id"]] += 1

                if is_clean:
                    clean_records += 1
                else:
                    flawed_records += 1
                    issue_counts[issue] += 1

            # Display progress
            print(
                f"Second {second + 1:02d}: "
                f"Generated {target_count} transactions"
            )

            # Maintain approximately one-second intervals
            elapsed = time.monotonic() - second_start
            remaining = 1.0 - elapsed

            if remaining > 0:
                time.sleep(remaining)

    except KeyboardInterrupt:
        print("\nGeneration stopped by user.")


# -------------------------------
# FINAL REPORT
# -------------------------------

total_time = time.monotonic() - start_time

duplicate_ids = {
    transaction_id: count
    for transaction_id, count in actual_duplicate_ids.items()
    if count > 1
}

print("\n========== GENERATION REPORT ==========")

print(f"Total records generated : {total_records}")
print(f"Clean records           : {clean_records}")
print(f"Flawed records          : {flawed_records}")

print(
    f"Actual clean percentage : "
    f"{(clean_records / total_records * 100):.2f}%"
    if total_records else "Actual clean percentage : 0%"
)

print(
    f"Actual flawed percentage: "
    f"{(flawed_records / total_records * 100):.2f}%"
    if total_records else "Actual flawed percentage: 0%"
)

print(f"Total execution time    : {total_time:.2f} seconds")
print(f"Average generation rate : {total_records / total_time:.2f} records/sec"
      if total_time else "Average generation rate : 0")

print("\nData Quality Issues:")

for issue, count in issue_counts.items():
    print(f"{issue:25s}: {count}")

print("\nDuplicate Transaction IDs:")

for transaction_id, count in duplicate_ids.items():
    print(f"{transaction_id}: {count} occurrences")

print(f"\nOutput saved to: {OUTPUT_FILE}")
print("=======================================")
