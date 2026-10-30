
import random
import uuid
from datetime import datetime, timezone
from faker import Faker # type: ignore

fake = Faker()

CURRENCIES = ["INR", "USD", "EUR", "GBP"]

TRANSACTION_TYPES = [
    "UPI",
    "CARD",
    "BANK_TRANSFER",
    "PAYMENT"
]

STATUSES = ["SUCCESS", "FAILED", "PENDING"]

SOURCES = [
    "MOBILE_APP",
    "WEB_APP",
    "PAYMENT_GATEWAY"
]


def generate_clean_transaction():
    """Generate a valid financial transaction."""

    return {
        "transaction_id": f"TXN-{uuid.uuid4().hex[:12]}",
        "account_id": f"ACC-{random.randint(1000, 9999)}",
        "amount": round(random.uniform(10, 100000), 2),
        "currency": random.choice(CURRENCIES),
        "transaction_type": random.choice(TRANSACTION_TYPES),
        "source": random.choice(SOURCES),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": random.choice(STATUSES),
        "merchant_id": f"MER-{random.randint(100, 999)}",
        "country": "IN",
        "schema_version": 1
    }


def inject_data_quality_issues(record):
    """Intentionally introduce one data-quality issue."""

    issue = random.choice([
        "missing_account",
        "negative_amount",
        "currency_format",
        "missing_merchant",
        "invalid_timestamp",
        "duplicate_transaction_id"
    ])

    if issue == "missing_account":
        record["account_id"] = None

    elif issue == "negative_amount":
        record["amount"] = -abs(record["amount"])

    elif issue == "currency_format":
        record["currency"] = random.choice(["inr", "₹"])

    elif issue == "missing_merchant":
        record.pop("merchant_id", None)

    elif issue == "invalid_timestamp":
        record["timestamp"] = "INVALID_TIMESTAMP"

    elif issue == "duplicate_transaction_id":
        record["transaction_id"] = "TXN-DUPLICATE-001"

    return record, issue


def generate_transaction():
    """
    Generate a transaction.
    85% clean records and 15% records with quality issues.
    """

    record = generate_clean_transaction()

    if random.random() < 0.15:
        record, issue = inject_data_quality_issues(record)
        return record, False, issue

    return record, True, None
