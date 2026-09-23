from pydantic import BaseModel


class AuthenticatedUser(BaseModel):
    uid: str
    email: str | None = None
    name: str | None = None
    email_verified: bool = False
    sign_in_provider: str | None = None
    role: str = "user"
    status: str = "active"
