from app.db.dependencies import get_database_client, get_lead_repository
from app.providers.dependencies import get_credential_cipher, get_provider_repository
from app.outreach.personalization import CompanyNamePreparer
from app.outreach.repository import OutreachRepository


def get_outreach_repository() -> OutreachRepository:
    return OutreachRepository(
        get_database_client(), get_credential_cipher(),
        company_name_preparer=CompanyNamePreparer(get_provider_repository()),
    )
