from fastapi import APIRouter, Depends # type: ignore
from sqlalchemy.orm import Session # type: ignore
from database import get_db
from services.athena_service import AthenaService

router = APIRouter(prefix="/health", tags=["System Health"])
athena = AthenaService()

@router.get("")
def system_health(db: Session = Depends(get_db)):
    """Verifies live health and connectivity for Neon PostgreSQL and AWS Athena."""
    # Check Neon database connection
    db_status = "healthy"
    try:
        db.execute("SELECT 1")
    except Exception:
        db_status = "unhealthy"

    # Check AWS Athena connection
    aws_status = "healthy"
    try:
        athena.client.list_work_groups()
    except Exception:
        aws_status = "unhealthy"

    overall = "healthy" if db_status == "healthy" and aws_status == "healthy" else "degraded"

    return {
        "status": overall,
        "database": db_status,
        "aws_athena": aws_status
    }