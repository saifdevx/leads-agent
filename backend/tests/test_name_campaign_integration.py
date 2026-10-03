from cryptography.fernet import Fernet

from app.leads.smart_data import repair_lead_row
from app.outreach.personalization import CompanyNamePreparer
from app.outreach.repository import OutreachRepository
from app.outreach.schemas import CampaignCreate, FollowUpCreate, TemplateCreate
from app.providers.security import CredentialCipher
from test_outreach_repository import SqliteAdapter


class Providers:
    def connected_credentials(self, user_id): return {}


class Website:
    def company_name(self, url): return None


class Leads:
    def get_leads_by_ids(self, user_id, ids):
        return [repair_lead_row({"id": "lead-1", "company_name": "Another roof DONE RIGHT✅ Here at our Manchester ...",
                                "email": "mpconstructionct@gmail.com", "website": "https://mqconstructionct.com"})]


def test_legacy_lead_subject_html_and_followups_use_the_same_safe_snapshot():
    repo = OutreachRepository(SqliteAdapter(), CredentialCipher(Fernet.generate_key().decode()),
                              company_name_preparer=CompanyNamePreparer(Providers(), crawler=Website()))
    template = repo.save_template("u", TemplateCreate(name="Intro", category="General", subject="For {{Business Name}}",
        body="{{greeting}}<br><strong>{{company_name}}</strong>"))
    followup = repo.save_template("u", TemplateCreate(name="Follow", category="General", subject="Following up with {{company_name}}",
        body="{{greeting}}<br>Checking in with {{Business Name}}."))
    sender = repo.save_hostinger_sender("u", "sender@example.com", "Sender", {"api_token": "test", "mailbox_resource_id": "AC123"})
    campaign, preview, _, _ = repo.create_campaign("u", CampaignCreate(name="Safe names", lead_ids=["lead-1"],
        template_id=template["id"], sender_id=sender["id"], follow_ups=[FollowUpCreate(template_id=followup["id"], delay_hours=24)]), Leads())
    assert campaign["status"] == "draft"
    assert preview[0]["subject"] == "For MQ Construction CT"
    assert "Hi MQ Construction CT team," in preview[0]["body"]
    messages = repo.database.execute("SELECT subject,body,status FROM email_messages ORDER BY step_number").rows
    assert len(messages) == 2 and messages[0]["status"] == "draft" and messages[1]["status"] == "waiting"
    assert all("MQ Construction CT" in row["subject"] and "Another roof" not in row["body"] for row in messages)
    assert repo.due_messages() == []
    repo.approve_campaign("u", campaign["id"])
    # Approval/delivery use the stored, reviewed copy; no last-minute re-render.
    assert repo.due_messages()[0]["body"] == preview[0]["body"]


def test_static_templates_do_not_spend_name_research_credits():
    class Unexpected:
        def prepare(self, *args): raise AssertionError("No name variables to resolve")
    repo = OutreachRepository(SqliteAdapter(), CredentialCipher(Fernet.generate_key().decode()), company_name_preparer=Unexpected())
    template = repo.save_template("u", TemplateCreate(name="Static", category="General", subject="Hello", body="Hi there"))
    sender = repo.save_gmail_sender("u", "sender@example.com", "Sender", {"access_token": "test"})
    campaign, _, _, _ = repo.create_campaign("u", CampaignCreate(name="Static copy", lead_ids=["lead-1"], template_id=template["id"], sender_id=sender["id"]), Leads())
    assert campaign["status"] == "draft"
