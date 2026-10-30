
import pandas as pd
import json
import os
from datetime import datetime, timezone

# ---------------------------------------
# CONFIGURATION
# ---------------------------------------

INPUT_FILE = "generated_transactions.jsonl"
OUTPUT_DIR = "output"

os.makedirs(OUTPUT_DIR, exist_ok=True)

SUPPORTED_CURRENCIES = {"INR", "USD", "EUR", "GBP"}
SUPPORTED_TYPES = {"UPI", "CARD", "BANK_TRANSFER", "PAYMENT"}
HIGH_VALUE_THRESHOLD = 50000


# ---------------------------------------
# 1. LOAD DATA
# ---------------------------------------

print("\n[1] Loading transaction data...")

df = pd.read_json(INPUT_FILE, lines=True)

total_records = len(df)

print(f"Loaded {total_records} transactions")


# ---------------------------------------
# 2. PRESERVE ORIGINAL DATA
# ---------------------------------------

df["original_record"] = df.apply(
    lambda row: json.dumps(
        row.drop(labels=["original_record"], errors="ignore").to_dict(),
        default=str
    ),
    axis=1
)

# Each record gets its own list of validation issues
df["validation_issues"] = [[] for _ in range(len(df))]


# ---------------------------------------
# 3. DATA NORMALIZATION
# ---------------------------------------

print("[2] Normalizing data...")

df["currency"] = (
    df["currency"]
    .astype("string")
    .str.strip()
    .str.upper()
)

df["transaction_type"] = (
    df["transaction_type"]
    .astype("string")
    .str.strip()
    .str.upper()
)

df["status"] = (
    df["status"]
    .astype("string")
    .str.strip()
    .str.upper()
)

df["amount"] = pd.to_numeric(
    df["amount"],
    errors="coerce"
)

df["parsed_timestamp"] = pd.to_datetime(
    df["timestamp"],
    errors="coerce",
    utc=True
)


# ---------------------------------------
# 4. DATA QUALITY VALIDATION
# ---------------------------------------

print("[3] Validating data quality...")

def add_issue(mask, issue_name):
    for index in df.index[mask.fillna(False)]:
        df.at[index, "validation_issues"].append(issue_name)


add_issue(
    df["transaction_id"].isna() |
    (df["transaction_id"].astype("string").str.strip() == ""),
    "missing_transaction_id"
)

add_issue(
    df["account_id"].isna() |
    (df["account_id"].astype("string").str.strip() == ""),
    "missing_account"
)

add_issue(
    df["merchant_id"].isna() |
    (df["merchant_id"].astype("string").str.strip() == ""),
    "missing_merchant"
)

add_issue(
    df["amount"].isna(),
    "invalid_amount"
)

add_issue(
    df["amount"] <= 0,
    "non_positive_amount"
)

add_issue(
    ~df["currency"].isin(SUPPORTED_CURRENCIES),
    "unsupported_currency"
)

add_issue(
    df["parsed_timestamp"].isna(),
    "invalid_timestamp"
)

add_issue(
    ~df["transaction_type"].isin(SUPPORTED_TYPES),
    "unsupported_transaction_type"
)


# ---------------------------------------
# 5. DUPLICATE DETECTION
# ---------------------------------------

print("[4] Detecting duplicate transactions...")

duplicate_mask = (
    df["transaction_id"].notna() &
    df["transaction_id"].duplicated(keep=False)
)

add_issue(duplicate_mask, "duplicate_transaction_id")


# ---------------------------------------
# 6. COMPLIANCE CHECKS
# ---------------------------------------

print("[5] Applying compliance rules...")

df["compliance_flag"] = "NONE"

high_value_mask = (
    (df["amount"] > HIGH_VALUE_THRESHOLD) &
    (df["amount"].notna())
)

df.loc[high_value_mask, "compliance_flag"] = "HIGH_VALUE_REVIEW"


# ---------------------------------------
# 7. CLASSIFICATION
# ---------------------------------------

print("[6] Classifying transactions...")

df["processing_status"] = df["validation_issues"].apply(
    lambda issues: "QUARANTINED" if issues else "CLEAN"
)

df["processing_timestamp"] = datetime.now(
    timezone.utc
).isoformat()

df["validation_reason"] = df["validation_issues"].apply(
    lambda issues: "; ".join(issues)
)


clean_df = df[df["processing_status"] == "CLEAN"].copy()

quarantine_df = df[
    df["processing_status"] == "QUARANTINED"
].copy()


# ---------------------------------------
# 8. SAVE OUTPUT
# ---------------------------------------

print("[7] Saving processed records...")

clean_df.drop(
    columns=["validation_issues"]
).to_csv(
    f"{OUTPUT_DIR}/clean_transactions.csv",
    index=False
)

quarantine_df.drop(
    columns=["validation_issues"]
).to_csv(
    f"{OUTPUT_DIR}/quarantined_transactions.csv",
    index=False
)


# ---------------------------------------
# 9. GENERATE PROCESSING REPORT
# ---------------------------------------

issue_counts = {}

for issues in df["validation_issues"]:
    for issue in issues:
        issue_counts[issue] = issue_counts.get(issue, 0) + 1

report = f"""
========== REGDATA ENGINE PROCESSING REPORT ==========

Total records processed : {total_records}
Clean records           : {len(clean_df)}
Quarantined records     : {len(quarantine_df)}

Clean percentage        : {len(clean_df) / total_records * 100:.2f}%
Quarantined percentage  : {len(quarantine_df) / total_records * 100:.2f}%

High-value transactions: {high_value_mask.sum()}

Data Quality Issues:
"""

for issue, count in issue_counts.items():
    report += f"{issue:<35}: {count}\n"

report += "\n=====================================================\n"

with open(
    f"{OUTPUT_DIR}/processing_report.txt",
    "w",
    encoding="utf-8"
) as file:
    file.write(report)

print(report)
print("Processing completed successfully!")
