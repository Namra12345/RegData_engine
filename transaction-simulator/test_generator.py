
import re
import unittest
from datetime import datetime

from generator import (
    SCHEMA_FIELDS,
    generate_record,
    generate_dataset,
)


class TestRegDataGenerator(unittest.TestCase):

    def test_schema_fields(self):
        record = generate_record()

        self.assertEqual(set(record.keys()), set(SCHEMA_FIELDS))
        self.assertEqual(len(record), 17)

    def test_valid_record_values(self):
        record = generate_record()

        self.assertTrue(record["event_id"].startswith("EVT-"))
        self.assertTrue(record["transaction_id"].startswith("TXN-"))
        self.assertTrue(record["account_id"].startswith("ACC-"))

        self.assertIsInstance(record["amount"], float)
        self.assertGreater(record["amount"], 0)

        self.assertIn(
            record["currency"],
            ["INR", "USD", "EUR", "GBP"]
        )

        self.assertIn(
            record["transaction_type"],
            ["UPI", "CARD", "BANK_TRANSFER", "PAYMENT"]
        )

        self.assertIn(record["direction"], ["DEBIT", "CREDIT"])

        self.assertIn(
            record["status"],
            ["SUCCESS", "FAILED", "PENDING"]
        )

        self.assertIn(
            record["source"],
            ["MOBILE_APP", "WEB_APP", "PAYMENT_GATEWAY"]
        )

        self.assertRegex(
            record["kyc_id"],
            r"^[A-Z]{5}[0-9]{4}[A-Z]$"
        )

        self.assertEqual(record["schema_version"], 1)

        datetime.fromisoformat(record["timestamp"])

    def test_generation_count(self):
        records, _ = generate_dataset(
            total_records=200,
            flawed_ratio=0.15,
            seed=42
        )

        self.assertEqual(len(records), 200)

    def test_intentionally_flawed_count(self):
        records, injected_issues = generate_dataset(
            total_records=200,
            flawed_ratio=0.15,
            seed=42
        )

        self.assertEqual(sum(injected_issues.values()), 30)

    def test_clean_dataset_event_ids_are_unique(self):
        records, _ = generate_dataset(
            total_records=200,
            flawed_ratio=0,
            seed=42
        )

        event_ids = [record["event_id"] for record in records]

        self.assertEqual(len(event_ids), len(set(event_ids)))

    def test_transaction_ids_are_generated(self):
        records, _ = generate_dataset(
            total_records=100,
            flawed_ratio=0,
            seed=42
        )

        transaction_ids = [
            record["transaction_id"] for record in records
        ]

        self.assertEqual(len(transaction_ids), len(set(transaction_ids)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
