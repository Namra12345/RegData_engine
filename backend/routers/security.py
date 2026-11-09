from fastapi import APIRouter, Depends # type: ignore
from auth.jwt import get_current_user, require_role
from models import User

router = APIRouter(prefix="/security", tags=["Security & Compliance Audit"])

@router.get("/status")
def security_status(current_user: User = Depends(require_role("admin", "compliance_officer"))):
    """Returns active security policy metrics and clearance levels."""
    return {
        "rbac_enforced": True,
        "pii_masking_active": True,
        "supported_roles": ["compliance_officer", "auditor", "data_engineer", "admin"],
        "user_clearance": current_user.role
    }