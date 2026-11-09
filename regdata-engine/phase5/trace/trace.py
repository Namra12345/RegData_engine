import json
import time
import boto3
import yaml
import os


SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "settings.yaml")


def load_settings():
    with open(SETTINGS_PATH) as f:
        return yaml.safe_load(f)


def run_athena_query(client, sql, output_location, database):
    response = client.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": database},
        ResultConfiguration={"OutputLocation": output_location}
    )
    execution_id = response["QueryExecutionId"]

    while True:
        result = client.get_query_execution(QueryExecutionId=execution_id)
        state = result["QueryExecution"]["Status"]["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(2)

    if state != "SUCCEEDED":
        reason = result["QueryExecution"]["Status"].get("StateChangeReason", "")
        raise RuntimeError(f"Athena query failed: {reason}")

    rows = []
    paginator = client.get_paginator("get_query_results")
    headers = None
    for page in paginator.paginate(QueryExecutionId=execution_id):
        for row in page["ResultSet"]["Rows"]:
            values = [c.get("VarCharValue", "") for c in row["Data"]]
            if headers is None:
                headers = values
            else:
                rows.append(dict(zip(headers, values)))
    return rows


def trace_transaction(transaction_id, date=None):
    settings = load_settings()
    client = boto3.client("athena", region_name=settings["athena"]["region"])
    output = settings["athena"]["output_location"]
    database = settings["athena"]["database"]

    date_filter = ""
    if date:
        date_filter = f"AND DATE(c.timestamp) = DATE '{date}'"

    # Check clean transactions first
    clean_sql = f"""
        SELECT
            c.transaction_id,
            c.event_id,
            c.account_id,
            c.amount,
            c.currency,
            c.transaction_type,
            c.direction,
            c.status,
            c.timestamp,
            c.rule_flags,
            c.processing_status,
            c.processed_at,
            c.source_topic,
            c.source_partition,
            c.source_offset,
            c.batch_id,
            c.processor_version,
            r.raw_payload
        FROM regdata.clean_transactions c
        JOIN regdata.raw_transactions r
          ON  r.source_topic     = c.source_topic
          AND r.source_partition = c.source_partition
          AND r.source_offset    = c.source_offset
        WHERE c.transaction_id = '{transaction_id}'
        {date_filter}
        LIMIT 1
    """

    rows = run_athena_query(client, clean_sql, output, database)

    if rows:
        row = rows[0]
        return {
            "status": "CLEAN",
            "transaction_id": row["transaction_id"],
            "event_id": row["event_id"],
            "account_id": row["account_id"],
            "amount": row["amount"],
            "currency": row["currency"],
            "transaction_type": row["transaction_type"],
            "direction": row["direction"],
            "transaction_status": row["status"],
            "timestamp": row["timestamp"],
            "rule_flags": row["rule_flags"],
            "processing_status": row["processing_status"],
            "processed_at": row["processed_at"],
            "lineage": {
                "source_topic": row["source_topic"],
                "source_partition": row["source_partition"],
                "source_offset": row["source_offset"],
                "batch_id": row["batch_id"],
                "processor_version": row["processor_version"],
                "raw_payload": row["raw_payload"]
            }
        }

    # Check quarantine if not in clean
    quarantine_sql = f"""
        SELECT
            q.transaction_id,
            q.event_id,
            q.error_codes,
            q.quarantined_at,
            q.source_topic,
            q.source_partition,
            q.source_offset,
            q.batch_id,
            q.raw_payload
        FROM regdata.quarantine_transactions q
        WHERE q.transaction_id = '{transaction_id}'
        LIMIT 1
    """

    rows = run_athena_query(client, quarantine_sql, output, database)

    if rows:
        row = rows[0]
        return {
            "status": "QUARANTINED",
            "transaction_id": row["transaction_id"],
            "event_id": row["event_id"],
            "error_codes": row["error_codes"],
            "quarantined_at": row["quarantined_at"],
            "lineage": {
                "source_topic": row["source_topic"],
                "source_partition": row["source_partition"],
                "source_offset": row["source_offset"],
                "batch_id": row["batch_id"],
                "raw_payload": row["raw_payload"]
            }
        }

    return {"status": "NOT_FOUND", "transaction_id": transaction_id}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 trace.py <transaction_id> [date]")
        sys.exit(1)

    txn_id = sys.argv[1]
    date = sys.argv[2] if len(sys.argv) > 2 else None
    result = trace_transaction(txn_id, date)
    print(json.dumps(result, indent=2))
