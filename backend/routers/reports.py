from fastapi import APIRouter, Depends # type: ignore
from services.athena_service import AthenaService
from auth.jwt import get_current_user
from models import User

router = APIRouter(prefix="/reports", tags=["Compliance Reports"])
athena = AthenaService()

@router.get("")
def list_reports(current_user: User = Depends(get_current_user)):
    """Fetches metadata for all generated compliance report runs."""
    try:
        reports = athena.get_reports_list()
        return {"items": reports}
    except Exception as e:
        return {"items": [], "message": str(e)}