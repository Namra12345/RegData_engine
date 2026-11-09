import os
import csv
import json
import time
import hashlib
import boto3
import yaml
from datetime import datetime, timezone


SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "settings.yaml")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "output")


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


def fetch_open_high_alerts(client, settings):
    sql = """
        SELECT
            alert_id, rule_id, rule_version, severity,
            account_id, window_start, txn_count,
            total_amount, evidence, status, data_as_of, created_at
        FROM regdata_governance.compliance_alerts
        WHERE severity = 'HIGH'
          AND status = 'NEW'
        ORDER BY created_at DESC
    """
    return run_athena_query(
        client, sql,
        settings["governance"]["output_location"],
        settings["governance"]["database"]
    )


def write_csv(rows, filepath):
    if not rows:
        return 0
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def upload_to_s3(s3_client, filepath, bucket, key):
    s3_client.upload_file(filepath, bucket, key)
    return f"s3://{bucket}/{key}"


def insert_report_run(client, settings, report):
    sql = f"""
        INSERT INTO regdata_governance.report_runs
        VALUES (
            '{report['report_id']}',
            CURRENT_TIMESTAMP,
            'make_report',
            '{report['rules_version']}',
            TIMESTAMP '{report['data_as_of']}',
            {report['row_count']},
            '{report['file_s3_path']}',
            '{report['file_sha256']}',
            ''
        )
    """
    run_athena_query(
        client, sql,
        settings["governance"]["output_location"],
        settings["governance"]["database"]
    )


def log_audit(client, settings, report_id, row_count):
    sql = f"""
        INSERT INTO regdata_governance.audit_log
        VALUES (
            CURRENT_TIMESTAMP,
            'make_report',
            'MAKE_REPORT',
            '{report_id}',
            '{json.dumps({"row_count": row_count}).replace("'", "''")}'
        )
    """
    run_athena_query(
        client, sql,
        settings["governance"]["output_location"],
        settings["governance"]["database"]
    )


def run():
    settings = load_settings()
    client = boto3.client("athena", region_name=settings["athena"]["region"])
    s3_client = boto3.client("s3", region_name=settings["athena"]["region"])

    now = datetime.now(timezone.utc)
    report_id = f"rpt-{now.strftime('%Y-%m-%d-%H%M')}"
    data_as_of = now.strftime("%Y-%m-%d %H:%M:%S")

    print(f"Fetching open HIGH alerts...")
    rows = fetch_open_high_alerts(client, settings)
    print(f"Found {len(rows)} alerts.")

    # Write CSV locally
    local_path = os.path.join(REPORTS_DIR, f"{report_id}.csv")
    row_count = write_csv(rows, local_path)

    if row_count == 0:
        print("No HIGH alerts found. Report not created.")
        return

    # Hash the file
    file_hash = sha256_file(local_path)

    # Upload to S3
    s3_key = f"governance/reports/{report_id}.csv"
    s3_path = upload_to_s3(
        s3_client, local_path,
        "regdata-engine-storage", s3_key
    )
    print(f"Report uploaded to {s3_path}")

    # Get git commit for rules version
    try:
        import subprocess
        rules_version = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.path.dirname(__file__)
        ).decode().strip()
    except Exception:
        rules_version = "unknown"

    report = {
        "report_id": report_id,
        "rules_version": rules_version,
        "data_as_of": data_as_of,
        "row_count": row_count,
        "file_s3_path": s3_path,
        "file_sha256": file_hash
    }

    # Write to report_runs table
    insert_report_run(client, settings, report)
    print(f"Report run recorded: {report_id}")

    # Write audit log
    log_audit(client, settings, report_id, row_count)

    print(f"\nReport complete:")
    print(f"  ID       : {report_id}")
    print(f"  Rows     : {row_count}")
    print(f"  S3 path  : {s3_path}")
    print(f"  SHA256   : {file_hash}")


if __name__ == "__main__":
    run()
