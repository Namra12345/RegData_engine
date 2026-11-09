from fastapi import APIRouter, Depends # type: ignore
from services.athena_service import AthenaService
from auth.jwt import get_current_user
from masking import mask_sensitive_data
from models import User

router = APIRouter(prefix="/overview", tags=["Overview & Metrics"])
athena = AthenaService()

@router.get("/summary")
def get_daily_summary(current_user: User = Depends(get_current_user)):
    """Fetches daily transaction summary metrics from Athena view v_daily_summary."""
    data = athena.get_daily_summary()
    # Apply masking per role
    masked_data = [mask_sensitive_data(row, current_user.role) for row in data]
    return {"items": masked_data}