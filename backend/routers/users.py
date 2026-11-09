from fastapi import APIRouter, Depends # type: ignore
from sqlalchemy.orm import Session # type: ignore
from database import get_db
from models import User
from auth.jwt import get_current_user, require_role

router = APIRouter(prefix="/users", tags=["User Management"])

@router.get("/me")
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Returns the authenticated user's profile details and role."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at
    }

@router.get("")
def list_all_users(db: Session = Depends(get_db), current_user: User = Depends(require_role("admin"))):
    """Lists all platform users. Restricted to administrators."""
    users = db.query(User).all()
    return {
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at
            }
            for u in users
        ]
    }