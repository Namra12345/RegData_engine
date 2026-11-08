from fastapi import APIRouter, Depends, HTTPException, status # type: ignore
from services.athena_service import AthenaService
from auth.jwt import get_current_user
from masking import mask_sensitive_data
from models import User

router = APIRouter(prefix="/trace", tags=["Transaction Lineage & Trace"])
athena = AthenaService()

@router.get("/{transaction_id}")
def trace_transaction(transaction_id: str, current_user: User = Depends(get_current_user)):
    """Traces a specific transaction across data layers, enforcing role-based PII masking."""
    # Updated table name from transactions to clean_transactions
    query = f"SELECT * FROM regdata.clean_transactions WHERE transaction_id = '{transaction_id}' LIMIT 1"
    try:
        results = athena._run_query(query)
        if not results:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        masked_record = mask_sensitive_data(results[0], current_user.role)
        return {"transaction": masked_record}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))