from fastapi import APIRouter, Depends # type: ignore
from services.athena_service import AthenaService
from auth.jwt import get_current_user
from masking import mask_sensitive_data
from models import User

router = APIRouter(prefix="/quality", tags=["Pipeline Health & Quality"])
athena = AthenaService()

@router.get("/health")
def get_pipeline_health(current_user: User = Depends(get_current_user)):
    """Fetches real-time pipeline execution health metrics."""
    data = athena.get_pipeline_health()
    return {"items": data}

@router.get("/metrics")
def get_data_quality_metrics(current_user: User = Depends(get_current_user)):
    """Fetches daily data quality quarantine error distribution metrics."""
    data = athena.get_data_quality_metrics()
    return {"items": data}