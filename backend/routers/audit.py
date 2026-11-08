from fastapi import APIRouter, Depends # type: ignore
from services.athena_service import AthenaService
from auth.jwt import get_current_user, require_role
from masking import mask_sensitive_data
from models import User

router = APIRouter(prefix="/audit", tags=["Audit Trail & Reports"])
athena = AthenaService()

@router.get("/logs")
def get_audit_logs(current_user: User = Depends(require_role("compliance_officer", "auditor", "admin"))):
    """Fetches governance audit trail logs. Restricted to compliance, auditors, and admins."""
    data = athena.get_audit_logs()
    masked_data = [mask_sensitive_data(row, current_user.role) for row in data]
    return {"items": masked_data}

@router.get("/reports")
def get_reports_list(current_user: User = Depends(get_current_user)):
    """Fetches metadata for generated compliance report runs."""
    data = athena.get_reports_list()
    return {"items": data}