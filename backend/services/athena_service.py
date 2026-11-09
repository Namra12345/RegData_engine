import os
import time
import boto3 # type: ignore
from cachetools import TTLCache, cached # type: ignore
from dotenv import load_dotenv # type: ignore

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
S3_OUTPUT_BUCKET = os.getenv("S3_OUTPUT_BUCKET", "s3://regdata-engine-storage/athena-results/")
ATHENA_DATABASE = os.getenv("ATHENA_DATABASE", "regdata")
GOVERNANCE_DATABASE = os.getenv("GOVERNANCE_DATABASE", "regdata_governance")
ATHENA_WORKGROUP = os.getenv("ATHENA_WORKGROUP", "primary")

# In-memory TTL cache: caches query results for 60 seconds to save Athena scan costs
query_cache = TTLCache(maxsize=100, ttl=60)

class AthenaService:
    def __init__(self):
        self.client = boto3.client("athena", region_name=AWS_REGION)

    def _run_query(self, query: str, database: str = ATHENA_DATABASE) -> list[dict]:
        """Executes an Athena query and returns results as a list of dictionaries."""
        response = self.client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={"Database": database},
            ResultConfiguration={"OutputLocation": S3_OUTPUT_BUCKET},
            WorkGroup=ATHENA_WORKGROUP
        )
        query_execution_id = response["QueryExecutionId"]

        # Poll for query completion
        while True:
            status_response = self.client.get_query_execution(QueryExecutionId=query_execution_id)
            state = status_response["QueryExecution"]["Status"]["State"]
            if state == "SUCCEEDED":
                break
            elif state in ["FAILED", "CANCELLED"]:
                reason = status_response["QueryExecution"]["Status"].get("StateChangeReason", "Unknown error")
                raise Exception(f"Athena query failed: {reason}")
            time.sleep(1)

        # Fetch results
        results_paginator = self.client.get_paginator("get_query_results")
        iterator = results_paginator.paginate(QueryExecutionId=query_execution_id)

        rows = []
        columns = []
        for page in iterator:
            resultSet = page["ResultSet"]
            if not columns and "ResultSetMetadata" in resultSet:
                columns = [col["Name"] for col in resultSet["ResultSetMetadata"]["ColumnInfo"]]
            
            for i, row in enumerate(resultSet["Rows"]):
                # Skip header row if it's the first page
                if not rows and i == 0 and len(columns) > 0:
                    # Check if the row matches columns (sometimes Athena includes header in rows)
                    values = [val.get("VarCharValue", None) for val in row["Data"]]
                    if values == columns:
                        continue
                
                values = [val.get("VarCharValue", None) for val in row["Data"]]
                if columns and len(values) == len(columns):
                    rows.append(dict(zip(columns, values)))

        return rows

    @cached(query_cache)
    def get_daily_summary(self) -> list[dict]:
        """Fetches summary metrics from Phase 4 view v_daily_summary with 60s cache."""
        query = f"SELECT * FROM {ATHENA_DATABASE}.v_daily_summary ORDER BY transaction_date DESC LIMIT 7"
        return self._run_query(query)

    @cached(query_cache)
    def get_pipeline_health(self) -> list[dict]:
        """Fetches real-time pipeline execution health metrics from v_pipeline_health."""
        query = f"SELECT * FROM {ATHENA_DATABASE}.v_pipeline_health ORDER BY batch_id DESC LIMIT 10"
        return self._run_query(query)

    @cached(query_cache)
    def get_data_quality_metrics(self) -> list[dict]:
        """Fetches daily quarantine error distribution from v_dq_quarantine_daily."""
        query = f"SELECT * FROM {ATHENA_DATABASE}.v_dq_quarantine_daily ORDER BY quarantine_date DESC LIMIT 10"
        return self._run_query(query)

    def get_compliance_alerts(self, severity: str = None, status: str = None) -> list[dict]:
        """Fetches compliance alerts from Phase 5 governance database."""
        query = f"SELECT * FROM {GOVERNANCE_DATABASE}.compliance_alerts"
        conditions = []
        if severity:
            conditions.append(f"severity = '{severity}'")
        if status:
            conditions.append(f"status = '{status}'")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY created_at DESC LIMIT 50"
        return self._run_query(query, database=GOVERNANCE_DATABASE)

    def update_alert_status(self, alert_id: str, new_status: str) -> bool:
        """Updates compliance alert status in governance storage/table."""
        # Note: Iceberg tables support UPDATE syntax directly in Athena
        query = f"UPDATE {GOVERNANCE_DATABASE}.compliance_alerts SET status = '{new_status}' WHERE alert_id = '{alert_id}'"
        self._run_query(query, database=GOVERNANCE_DATABASE)
        return True

    def get_audit_logs(self) -> list[dict]:
        """Fetches audit trail records from Phase 5 governance audit_log."""
        query = f"SELECT * FROM {GOVERNANCE_DATABASE}.audit_log ORDER BY event_time DESC LIMIT 50"
        return self._run_query(query, database=GOVERNANCE_DATABASE)

    def get_reports_list(self) -> list[dict]:
        """Fetches generated reports metadata from report_runs table."""
        query = f"SELECT * FROM {GOVERNANCE_DATABASE}.report_runs ORDER BY created_at DESC LIMIT 20"
        return self._run_query(query, database=GOVERNANCE_DATABASE)