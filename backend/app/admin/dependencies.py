from fastapi import Depends, HTTPException

from app.auth.dependencies import get_current_user
from app.auth.schemas import AuthenticatedUser
from app.core.config import get_settings
from app.db.dependencies import get_user_repository
from app.db.user_repository import UserRepository


def require_admin(
    current_user: AuthenticatedUser = Depends(get_current_user),
    repository: UserRepository = Depends(get_user_repository),
) -> AuthenticatedUser:
    settings = get_settings()
    if str(current_user.email or "").lower() in settings.admin_email_list:
        return current_user.model_copy(update={"role": "admin"})
    row = repository.get_by_firebase_uid(current_user.uid)
    if row and str(row.get("role") or "user") == "admin" and str(row.get("status") or "active") == "active":
        return current_user.model_copy(update={"role": "admin"})
    raise HTTPException(status_code=403, detail="Administrator access required.")
