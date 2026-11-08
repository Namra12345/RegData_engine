from fastapi import APIRouter, Depends, HTTPException, status # type: ignore
from pydantic import BaseModel # type: ignore
from typing import Optional
from services.athena_service import AthenaService
from auth.jwt import get_current_user, require_role
from masking import mask_sensitive_data
from models import User

router = APIRouter(prefix="/alerts", tags=["Compliance Alerts"])
athena = AthenaService()

class AlertStatusUpdate(BaseModel):
    status: str  # e.g., REVIEWED, CLOSED

@router.get("")
def list_compliance_alerts(
    severity: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Fetches compliance alerts with optional filtering by severity and status."""
    alerts = athena.get_compliance_alerts(severity=severity, status=status_filter)
    masked_alerts = [mask_sensitive_data(alert, current_user.role) for alert in alerts]
    return {"items": masked_alerts}

@router.patch("/{alert_id}")
def update_alert(
    alert_id: str,
    body: AlertStatusUpdate,
    current_user: User = Depends(require_role("compliance_officer", "admin"))
):
    """Updates an alert's status. Restricted to compliance officers and admins."""
    try:
        athena.update_alert_status(alert_id, body.status)
        return {"success": True, "message": f"Alert {alert_id} status updated to {body.status}"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )