import os
import hashlib
import json
import time
import boto3
import yaml
from datetime import datetime, timezone


RULES_DIR = os.path.join(os.path.dirname(__file__), "rules")
SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "settings.yaml")


def load_settings():
    with open(SETTINGS_PATH) as f:
        return yaml.safe_load(f)


def load_rules():
    rules = []
    for fname in sorted(os.listdir(RULES_DIR)):
        if fname.endswith(".yaml"):
            with open(os.path.join(RULES_DIR, fname)) as f:
                rules.append(yaml.safe_load(f))
    return rules


def make_alert_id(rule_id, account_id, window_start):
    key = f"{rule_id}|{account_id}|{window_start}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


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
    pages = paginator.paginate(QueryExecutionId=execution_id)
    headers = None
    for page in pages:
        for i, row in enumerate(page["ResultSet"]["Rows"]):
            values = [c.get("VarCharValue", "") for c in row["Data"]]
            if headers is None:
                headers = values
            else:
                rows.append(dict(zip(headers, values)))
    return rows


def insert_alert(client, settings, alert):
    sql = f"""
        INSERT INTO {settings['governance']['database']}.compliance_alerts
        VALUES (
            '{alert['alert_id']}',
            '{alert['rule_id']}',
            {alert['rule_version']},
            '{alert['severity']}',
            '{alert['account_id']}',
            TIMESTAMP '{alert['window_start']}',
            {alert['txn_count']},
            {alert['total_amount']},
            '{alert['evidence']}',
            'NEW',
            TIMESTAMP '{alert['data_as_of']}',
            CURRENT_TIMESTAMP
        )
    """
    run_athena_query(
        client, sql,
        settings['governance']['output_location'],
        settings['governance']['database']
    )


def log_audit(client, settings, action, target, details):
    sql = f"""
        INSERT INTO {settings['governance']['database']}.audit_log
        VALUES (
            CURRENT_TIMESTAMP,
            'run_rules',
            '{action}',
            '{target}',
            '{json.dumps(details).replace("'", "''")}'
        )
    """
    run_athena_query(
        client, sql,
        settings['governance']['output_location'],
        settings['governance']['database']
    )


def send_sns_summary(settings, high_alerts, as_of):
    try:
        sns = boto3.client("sns", region_name=settings["athena"]["region"])
        topic_arn = settings.get("sns_topic_arn", "arn:aws:sns:ap-south-1:776163183407:regdata-alerts")

        lines = [f"RegData Compliance Engine — HIGH Alerts ({as_of})\n"]
        for a in high_alerts:
            lines.append(
                f"  Rule: {a['rule_id']} | Account: {a['account_id']} | "
                f"Window: {a['window_start']} | Txns: {a['txn_count']}"
            )

        sns.publish(
            TopicArn=topic_arn,
            Subject=f"RegData — {len(high_alerts)} HIGH alert(s) found",
            Message="\n".join(lines)
        )
        print(f"[SNS] Alert email sent — {len(high_alerts)} HIGH alert(s)")
    except Exception as e:
        print(f"[SNS] Failed to send alert: {e}")


def run(as_of=None):
    settings = load_settings()
    rules = load_rules()

    if as_of is None:
        as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    client = boto3.client("athena", region_name=settings["athena"]["region"])

    total_alerts = 0
    all_alerts = []

    for rule in rules:
        print(f"Running rule {rule['id']}...")

        thresholds = settings.get("thresholds", {})
        sql = rule["sql"].format(as_of=as_of, **thresholds)

        try:
            rows = run_athena_query(
                client, sql,
                settings["athena"]["output_location"],
                settings["athena"]["database"]
            )
        except Exception as e:
            print(f"  Rule {rule['id']} failed: {e}")
            continue

        for row in rows:
            account_id = row.get("account_id", "")
            window_start = row.get("window_start", as_of)
            alert_id = make_alert_id(rule["id"], account_id, window_start)

            evidence = json.dumps(row.get("evidence_list", "").split(",")[:10])

            alert = {
                "alert_id": alert_id,
                "rule_id": rule["id"],
                "rule_version": rule["version"],
                "severity": rule["severity"],
                "account_id": account_id,
                "window_start": window_start,
                "txn_count": row.get("txn_count", 0),
                "total_amount": row.get("total_amount", 0),
                "evidence": evidence.replace("'", "''"),
                "data_as_of": as_of
            }

            try:
                insert_alert(client, settings, alert)
                total_alerts += 1
                all_alerts.append(alert)
                print(f"  Alert {alert_id} written for account {account_id}")
            except Exception as e:
                print(f"  Failed to write alert: {e}")

    log_audit(client, settings, "RUN_RULES", "compliance_alerts", {
        "rules_run": len(rules),
        "alerts_written": total_alerts,
        "as_of": as_of
    })

    # Send one SNS email per run if any HIGH alerts were written
    high_alerts = [a for a in all_alerts if a["severity"] == "HIGH"]
    if high_alerts:
        send_sns_summary(settings, high_alerts, as_of)

    print(f"\nDone. {len(rules)} rules run, {total_alerts} alerts written.")


if __name__ == "__main__":
    run()
