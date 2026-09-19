from app.db.dependencies import get_database_client, get_lead_repository
from app.providers.dependencies import get_credential_cipher
from app.outreach.repository import OutreachRepository


def get_outreach_repository() -> OutreachRepository:
    return OutreachRepository(get_database_client(), get_credential_cipher())
