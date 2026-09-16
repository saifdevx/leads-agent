from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.auth.schemas import AuthenticatedUser

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/me", response_model=AuthenticatedUser)
def read_current_user(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Return the identity established by a verified Firebase ID token."""
    return current_user
