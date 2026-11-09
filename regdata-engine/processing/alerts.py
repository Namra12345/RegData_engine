import json
import boto3

from config.spark_config import AWS_REGION, SNS_TOPIC_ARN


_sns_client = None


def _get_client():
    global _sns_client
    if _sns_client is None:
        _sns_client = boto3.client("sns", region_name=AWS_REGION)
    return _sns_client


def _publish(subject, payload):
    try:
        _get_client().publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=json.dumps(payload, indent=2, default=str)
        )
        print(f"[ALERT SENT] {subject}")
    except Exception as e:
        # Never let an alert failure crash the pipeline
        print(f"[ALERT FAILED] {subject} — {e}")


def alert_reconciliation_failed(batch_id, records_in, records_clean, records_quarantined):
    _publish(
        subject=f"RegData RECONCILIATION FAILED — Batch {batch_id}",
        payload={
            "alert_type": "RECONCILIATION_FAILED",
            "batch_id": batch_id,
            "records_in": records_in,
            "records_clean": records_clean,
            "records_quarantined": records_quarantined,
            "difference": records_in - records_clean - records_quarantined
        }
    )


def alert_high_quarantine_rate(batch_id, records_in, records_quarantined, rate):
    _publish(
        subject=f"RegData HIGH QUARANTINE RATE — Batch {batch_id}",
        payload={
            "alert_type": "HIGH_QUARANTINE_RATE",
            "batch_id": batch_id,
            "records_in": records_in,
            "records_quarantined": records_quarantined,
            "quarantine_rate_pct": round(rate * 100, 2)
        }
    )
