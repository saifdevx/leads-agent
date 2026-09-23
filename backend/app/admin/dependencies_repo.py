from app.admin.repository import AdminRepository
from app.db.dependencies import get_database_client


def get_admin_repository() -> AdminRepository:
    return AdminRepository(get_database_client())
