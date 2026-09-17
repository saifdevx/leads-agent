from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_application_user
from app.auth.schemas import AuthenticatedUser

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/me", response_model=AuthenticatedUser)
def read_current_user(
    current_user: AuthenticatedUser = Depends(get_current_application_user),
) -> AuthenticatedUser:
    """Return the verified Firebase identity after syncing its Turso user record."""
    return current_user
