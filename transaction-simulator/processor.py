
import argparse
import json
import os
import re
from datetime import datetime, timezone

import pandas as pd


# ---------------------------------------
# CONFIGURATION
# ---------------------------------------

INPUT_FILE = "generated_transactions.jsonl"
OUTPUT_DIR = "output"

REQUIRED_FIELDS = [
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

SUPPORTED_CURRENCIES = {"INR", "USD", "EUR", "GBP"}
SUPPORTED_TYPES = {"UPI", "CARD", "BANK_TRANSFER", "PAYMENT"}
SUPPORTED_DIRECTIONS = {"DEBIT", "CREDIT"}
SUPPORTED_SOURCES = {"MOBILE_APP", "WEB_APP", "PAYMENT_GATEWAY"}
SUPPORTED_STATUSES = {"SUCCESS", "FAILED", "PENDING"}

# ISO country codes used by this synthetic-data prototype
SUPPORTED_COUNTRIES = {"IN", "AE", "US", "GB", "DE", "SG"}

# Prototype review threshold, not a regulatory reporting threshold
HIGH_VALUE_INR_THRESHOLD = 50000

PAN_PATTERN = r"^[A-Z]{5}[0-9]{4}[A-Z]$"


# ---------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------

def is_missing(series):
    """Identify null, empty, or whitespace-only values."""
    return (
        series.isna()
        | series.astype("string").str.strip().eq("").fillna(False)
    )


def normalize_name(value):
    """
    Standardize the display format of a name.
    This does not establish that two name variations are the same person.
    """
    if pd.isna(value):
        return None

    name = str(value).strip().upper()
    name = name.replace("_", " ")
    name = re.sub(r"\s+", " ", name)

    return name


def add_issue(df, mask, issue_name):
    """Add a validation issue to every matching row."""
    mask = mask.fillna(False)

    for index in df.index[mask]:
        df.at[index, "validation_issues"].append(issue_name)


def add_review_flag(df, mask, flag_name):
    """Add a compliance review flag to every matching row."""
    mask = mask.fillna(False)

    for index in df.index[mask]:
        df.at[index, "review_flags"].append(flag_name)


# ---------------------------------------
# 1. LOAD DATA
# ---------------------------------------

def process_transactions(input_file, output_dir):

    os.makedirs(output_dir, exist_ok=True)

    print("\n[1] Loading transaction data...")

    df = pd.read_json(input_file, lines=True)

    total_records = len(df)

    if total_records == 0:
        raise ValueError("Input file contains no transaction records.")

    print(f"Records loaded: {total_records}")

    # Preserve the original input record before transformations.
    df["raw_record"] = df.apply(
        lambda row: json.dumps(
            row.to_dict(),
            default=str
        ),
        axis=1
    )

    # ---------------------------------------
    # 2. SCHEMA VALIDATION
    # ---------------------------------------

    print("[2] Checking schema...")

    missing_schema_fields = []

    for field in REQUIRED_FIELDS:
        if field not in df.columns:
            df[field] = None
            missing_schema_fields.append(field)

    df["validation_issues"] = [[] for _ in range(len(df))]
    df["review_flags"] = [[] for _ in range(len(df))]

    for field in missing_schema_fields:
        add_issue(
            df,
            pd.Series(True, index=df.index),
            f"missing_schema_field_{field}"
        )

    # ---------------------------------------
    # 3. NORMALIZATION
    # ---------------------------------------

    print("[3] Normalizing data...")

    df["normalized_customer_name"] = (
        df["customer_name"].apply(normalize_name)
    )

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

    df["direction"] = (
        df["direction"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    df["source"] = (
        df["source"]
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

    df["country"] = (
        df["country"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    df["counterparty_country"] = (
        df["counterparty_country"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    df["kyc_id"] = (
        df["kyc_id"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    df["amount"] = pd.to_numeric(
        df["amount"],
        errors="coerce"
    )

    df["schema_version"] = pd.to_numeric(
        df["schema_version"],
        errors="coerce"
    )

    df["parsed_timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
        utc=True
    )

    # ---------------------------------------
    # 4. REQUIRED FIELD VALIDATION
    # ---------------------------------------

    print("[4] Validating required fields...")

    required_text_fields = [
        "event_id",
        "transaction_id",
        "account_id",
        "customer_name",
        "kyc_id",
        "counterparty_account_id",
        "counterparty_country",
        "currency",
        "transaction_type",
        "direction",
        "source",
        "timestamp",
        "status",
        "merchant_id",
        "country",
    ]

    for field in required_text_fields:
        add_issue(
            df,
            is_missing(df[field]),
            f"missing_{field}"
        )

    # ---------------------------------------
    # 5. FIELD FORMAT VALIDATION
    # ---------------------------------------

    print("[5] Validating field formats...")

    add_issue(
        df,
        df["kyc_id"].notna()
        & ~df["kyc_id"].str.fullmatch(PAN_PATTERN, na=False),
        "invalid_kyc_format"
    )

    add_issue(
        df,
        df["amount"].isna(),
        "invalid_amount"
    )

    add_issue(
        df,
        df["amount"].notna() & df["amount"].le(0),
        "non_positive_amount"
    )

    add_issue(
        df,
        ~df["currency"].isin(SUPPORTED_CURRENCIES),
        "unsupported_currency"
    )

    add_issue(
        df,
        ~df["transaction_type"].isin(SUPPORTED_TYPES),
        "unsupported_transaction_type"
    )

    add_issue(
        df,
        ~df["direction"].isin(SUPPORTED_DIRECTIONS),
        "invalid_direction"
    )

    add_issue(
        df,
        ~df["source"].isin(SUPPORTED_SOURCES),
        "unsupported_source"
    )

    add_issue(
        df,
        ~df["status"].isin(SUPPORTED_STATUSES),
        "unsupported_status"
    )

    add_issue(
        df,
        ~df["country"].isin(SUPPORTED_COUNTRIES),
        "unsupported_country"
    )

    add_issue(
        df,
        ~df["counterparty_country"].isin(SUPPORTED_COUNTRIES),
        "unsupported_counterparty_country"
    )

    add_issue(
        df,
        df["parsed_timestamp"].isna(),
        "invalid_timestamp"
    )

    add_issue(
        df,
        ~df["schema_version"].isin([1, 2]),
        "unsupported_schema_version"
    )

    # ---------------------------------------
    # 6. EVENT DEDUPLICATION
    # ---------------------------------------

    print("[6] Detecting duplicate events...")

    duplicate_event_mask = (
        df["event_id"].notna()
        & df["event_id"].duplicated(keep=False)
    )

    add_issue(
        df,
        duplicate_event_mask,
        "duplicate_event_id"
    )

    # Repeated transaction_id values are allowed.
    # A transaction may generate multiple distinct events.

    # ---------------------------------------
    # 7. COMPLIANCE REVIEW RULES
    # ---------------------------------------

    print("[7] Applying compliance review rules...")

    # High-value INR transaction review
    high_value_mask = (
        df["currency"].eq("INR")
        & df["amount"].gt(HIGH_VALUE_INR_THRESHOLD)
    )

    add_review_flag(
        df,
        high_value_mask,
        "HIGH_VALUE_INR_REVIEW"
    )

    # Cross-border review
    cross_border_mask = (
        df["country"].notna()
        & df["counterparty_country"].notna()
        & df["country"].ne(df["counterparty_country"])
        & df["transaction_type"].eq("BANK_TRANSFER")
    )

    add_review_flag(
        df,
        cross_border_mask,
        "CROSS_BORDER_TRANSFER_REVIEW"
    )

    # Large debit review
    large_debit_mask = (
        df["direction"].eq("DEBIT")
        & df["currency"].eq("INR")
        & df["amount"].gt(HIGH_VALUE_INR_THRESHOLD)
    )

    add_review_flag(
        df,
        large_debit_mask,
        "LARGE_DEBIT_REVIEW"
    )

    # ---------------------------------------
    # 8. CLASSIFICATION
    # ---------------------------------------

    print("[8] Classifying transactions...")

    df["processing_status"] = df["validation_issues"].apply(
        lambda issues: (
            "QUARANTINED" if issues else "CLEAN"
        )
    )

    df["compliance_status"] = df["review_flags"].apply(
        lambda flags: (
            "REVIEW_REQUIRED" if flags else "NO_REVIEW_FLAG"
        )
    )

    df["validation_reason"] = df["validation_issues"].apply(
        lambda issues: "; ".join(issues)
    )

    df["compliance_review_reasons"] = df["review_flags"].apply(
        lambda flags: "; ".join(flags)
    )

    df["processing_timestamp"] = datetime.now(
        timezone.utc
    ).isoformat()

    clean_df = df[
        df["processing_status"] == "CLEAN"
    ].copy()

    quarantine_df = df[
        df["processing_status"] == "QUARANTINED"
    ].copy()

    flagged_df = df[
        df["review_flags"].apply(bool)
    ].copy()

    # ---------------------------------------
    # 9. SAVE OUTPUT
    # ---------------------------------------

    print("[9] Saving output files...")

    clean_df.drop(
        columns=["validation_issues", "review_flags"]
    ).to_csv(
        os.path.join(output_dir, "clean_transactions.csv"),
        index=False
    )

    quarantine_df.drop(
        columns=["validation_issues", "review_flags"]
    ).to_csv(
        os.path.join(output_dir, "quarantined_transactions.csv"),
        index=False
    )

    flagged_df.drop(
        columns=["validation_issues", "review_flags"]
    ).to_csv(
        os.path.join(output_dir, "flagged_transactions.csv"),
        index=False
    )

    # ---------------------------------------
    # 10. PROCESSING REPORT
    # ---------------------------------------

    issue_counts = {}

    for issues in df["validation_issues"]:
        for issue in issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

    review_counts = {}

    for flags in df["review_flags"]:
        for flag in flags:
            review_counts[flag] = review_counts.get(flag, 0) + 1

    report = f"""
========== REGDATA ENGINE PROCESSING REPORT ==========

Total records processed : {total_records}
Clean records           : {len(clean_df)}
Quarantined records     : {len(quarantine_df)}
Compliance flagged      : {len(flagged_df)}

Clean percentage        : {len(clean_df) / total_records * 100:.2f}%
Quarantined percentage  : {len(quarantine_df) / total_records * 100:.2f}%

DATA QUALITY ISSUES:
"""

    for issue, count in sorted(issue_counts.items()):
        report += f"{issue:<40}: {count}\n"

    report += "\nCOMPLIANCE REVIEW FLAGS:\n"

    for flag, count in sorted(review_counts.items()):
        report += f"{flag:<40}: {count}\n"

    report += "\n=====================================================\n"

    report_path = os.path.join(
        output_dir,
        "processing_report.txt"
    )

    with open(report_path, "w", encoding="utf-8") as file:
        file.write(report)

    print(report)
    print(f"Processing completed. Results saved in: {output_dir}")


# ---------------------------------------
# MAIN
# ---------------------------------------

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="RegData Engine transaction processor"
    )

    parser.add_argument(
        "--input",
        default=INPUT_FILE
    )

    parser.add_argument(
        "--output",
        default=OUTPUT_DIR
    )

    args = parser.parse_args()

    process_transactions(
        input_file=args.input,
        output_dir=args.output
    )
