import pytest
from cryptography.fernet import Fernet

from app.leads.company_names import clean_company_name, is_directory_title
from app.leads.identity import identity_issue, recipient_issue
from app.leads.smart_data import infer_company_name, repair_lead_row
from app.leads.crawler import _best_email, _jsonld_business_names
from app.outreach.rendering import render_template
from app.outreach.repository import OutreachRepository
from app.outreach.schemas import CampaignCreate, TemplateCreate, FollowUpCreate
from app.outreach.safety import OutreachSafetyError, assert_message_safe
from app.outreach import sending, worker
from app.providers.security import CredentialCipher
from test_outreach_repository import SqliteAdapter

TITLE = 'Top 25 Solar installers based in London, United Kingdom'
BAD = {'id': 'directory', 'company_name': TITLE, 'email': 'sales@revenuebase.ai', 'website': 'https://revenuebase.ai', 'source_url': 'https://revenuebase.ai/blog/top-25-solar-installers-in-london'}
GOOD = {'id': 'good', 'company_name': 'Acme Solar', 'email': 'hello@acme.test', 'website': 'https://acme.test'}
UNKNOWN = {'id': 'unknown', 'company_name': 'PROJECT COMPLETE ...', 'email': 'john.smith@gmail.com'}


@pytest.mark.parametrize('title', [TITLE, 'Best 10 Roofing Contractors', 'Solar installers based in London', 'Directory of UK roofers', 'List of solar companies', 'Leading solar companies', '25 best contractors in London'])
def test_ranked_directory_titles_are_not_names(title):
    assert is_directory_title(title)
    assert clean_company_name(title) is None
    assert infer_company_name({'company_name': title, 'email': 'sales@directory.test'}) is None


@pytest.mark.parametrize('name', ['Top Roofing Ltd', 'M21 Roofing LTD', '3M', "Jim's Roofers", 'Top 10 Ltd'])
def test_actual_brands_not_arbitrarily_rewritten(name):
    # A genuine numeral-ranking-like brand needs stronger identity evidence;
    # Top 10 Ltd is intentionally held, not guessed, unlike Top Roofing Ltd.
    if name == 'Top 10 Ltd':
        assert clean_company_name(name) is None
    else:
        assert clean_company_name(name) == name


def test_user_screenshot_not_renamed_to_directory_operator():
    row = repair_lead_row(BAD)
    assert row['company_name'] is None and row['company_name_status'] == 'review_required'
    assert 'Directory' in row['outreach_block_reason']
    assert repair_lead_row(row)['outreach_block_reason']
    assert infer_company_name(row) is None


def test_domain_conflict_is_held_not_neutralized():
    row = repair_lead_row({**GOOD, 'email': 'sales@otherbusiness.test'})
    assert row['company_name'] is None
    assert 'differs' in row['outreach_block_reason']


@pytest.mark.parametrize('email,website', [('info@acme.co.uk', 'https://www.acme.co.uk'), ('info@mail.acme.test', 'https://acme.test'), ('mpconstructionct@gmail.com', 'https://mqconstructionct.com')])
def test_subdomains_and_public_mailboxes_not_declared_mismatched(email, website):
    assert identity_issue({'company_name': 'Acme', 'email': email, 'website': website}) is None


@pytest.mark.parametrize('email', ['broken@@example.com', 'a@bad', 'a..b@example.com', 'noreply@example.com', 'postmaster@example.com', 'person@example.com\r\nBcc: evil@example.com'])
def test_invalid_or_system_mailboxes_are_not_sendable(email):
    assert recipient_issue(email)


def test_unknown_name_neutral_subject_greeting_body_plain_and_html():
    row = repair_lead_row(UNKNOWN)
    assert not row['company_name'] and not row['outreach_block_reason']
    assert render_template('Free sample for {{company_name}}', row, {}, subject=True) == 'Free sample'
    assert render_template('Hi {{Business Name}} team,', row, {}) == 'Hi there,'
    assert render_template('Hi <strong>{{Business Name}}</strong> team,', row, {}) == 'Hi there,'
    body = render_template('{{greeting}}<br>I would like to help {{Business Name}}.', row, {})
    assert body == 'Hi there,<br>I would like to help your company.'
    assert_message_safe(row['email'], 'Free sample', body, row)


def test_exact_bad_literal_is_repaired_only_before_preview():
    row = repair_lead_row(UNKNOWN)
    text = 'Hi PROJECT COMPLETE ... team,\nI came across PROJECT COMPLETE ...'
    assert render_template(text, row, {}) == 'Hi there,\nI came across your company'
    assert render_template('Other business literal stays unchanged.', row, {}) == 'Other business literal stays unchanged.'


def test_html_name_is_escaped_and_does_not_change_subject_text():
    row = {'company_name': 'A & B Roofing', 'email': 'hello@ab.test'}
    assert render_template('<strong>{{company_name}}</strong>', row, {}) == '<strong>A &amp; B Roofing</strong>'
    assert render_template('For {{company_name}}', row, {}, subject=True) == 'For A & B Roofing'


def test_crawler_rejects_unrelated_corporate_footer_email_and_external_org():
    assert _best_email(['sales@webdesigner.test'], 'https://acme.test') is None
    assert _best_email(['sales@webdesigner.test', 'acmeroofing@gmail.com'], 'https://acme.test') == 'acmeroofing@gmail.com'
    assert _best_email(['sales@webdesigner.test', 'hello@acme.test'], 'https://acme.test') == 'hello@acme.test'
    assert _jsonld_business_names(['{"@type":"Organization","name":"Web Designer","url":"https://designer.test"}'], 'https://acme.test') == []


@pytest.mark.parametrize('subject,body', [('Free sample for ' + TITLE, 'Hi there,'), ('Hello', 'Hi ' + TITLE + ' team,'), ('Hello', 'Hi Another roof DONE RIGHT✅ Here at our Manchester ... team,'), ('Hello', 'Hi {{company_name}} team,'), ('Hello\nBcc: x', 'Hi there,')])
def test_final_guard_catches_legacy_or_manually_pasted_bad_copy(subject, body):
    with pytest.raises(OutreachSafetyError):
        assert_message_safe('person@example.com', subject, body)


def setup_campaign(leads, body='{{greeting}}<br>A free sample for {{Business Name}}.', subject='Free sample for {{Business Name}}', follow=False):
    repo = OutreachRepository(SqliteAdapter(), CredentialCipher(Fernet.generate_key().decode()))
    template = repo.save_template('u', TemplateCreate(name='Intro', category='General', subject=subject, body=body))
    sender = repo.save_hostinger_sender('u', 'sender@example.com', 'Sender', {'api_token': 'test', 'mailbox_resource_id': 'box'})
    class LeadRows:
        def get_leads_by_ids(self, user_id, ids): return leads
    data = CampaignCreate(name='Test', lead_ids=[x['id'] for x in leads], template_id=template['id'], sender_id=sender['id'],
        follow_ups=[FollowUpCreate(template_id=template['id'], delay_hours=24)] if follow else [])
    return repo, data, LeadRows()


def test_campaign_excludes_directory_conflict_and_duplicate_but_keeps_unknown():
    rows = [BAD, GOOD, {**GOOD, 'id': 'dupe', 'email': 'HELLO@ACME.TEST'}, UNKNOWN, {**GOOD, 'id': 'wrong', 'email': 'hello@other.test'}]
    repo, data, leads = setup_campaign(rows, follow=True)
    campaign, preview, suppressed, missing = repo.create_campaign('u', data, leads)
    assert campaign['recipient_count'] == 2 and campaign['unsafe_count'] == 2 and campaign['duplicate_count'] == 1
    assert campaign['skipped_count'] == 3 and suppressed == 0 and missing == 0
    assert len(preview) == 2 and all(TITLE not in item['body'] for item in preview)
    assert preview[1]['body'].startswith('Hi there,') and preview[1]['subject'] == 'Free sample'
    assert repo.database.execute('SELECT COUNT(*) AS n FROM email_messages').rows[0]['n'] == 4
    repo.approve_campaign('u', campaign['id'])
    assert len(repo.due_messages()) == 2


def test_all_unsafe_creates_no_campaign_or_messages():
    repo, data, leads = setup_campaign([BAD])
    with pytest.raises(ValueError, match='Directory'):
        repo.create_campaign('u', data, leads)
    assert repo.list_campaigns('u') == []
    assert repo.database.execute('SELECT COUNT(*) AS n FROM email_messages').rows[0]['n'] == 0


def test_invalid_literal_template_fails_before_database_write():
    repo, data, leads = setup_campaign([GOOD], body='Hi ' + TITLE + ' team,')
    with pytest.raises(ValueError): repo.create_campaign('u', data, leads)
    assert repo.list_campaigns('u') == []


def test_approval_and_resume_check_stored_copy_without_rewriting():
    repo, data, leads = setup_campaign([GOOD])
    campaign, preview, _, _ = repo.create_campaign('u', data, leads)
    with pytest.raises(ValueError, match='approve'): repo.set_campaign_status('u', campaign['id'], 'sending')
    bad_body = 'Hi ' + TITLE + ' team,'
    repo.database.execute('UPDATE email_messages SET body=?', (bad_body,), False)
    with pytest.raises(OutreachSafetyError): repo.approve_campaign('u', campaign['id'])
    assert repo._campaign_row('u', campaign['id'])['status'] == 'draft'
    assert repo.database.execute('SELECT body FROM email_messages').rows[0]['body'] == bad_body
    repo.database.execute('UPDATE email_messages SET body=?', (preview[0]['body'],), False)
    repo.approve_campaign('u', campaign['id'])
    repo.set_campaign_status('u', campaign['id'], 'paused')
    repo.database.execute('UPDATE email_messages SET body=?', (bad_body,), False)
    with pytest.raises(OutreachSafetyError): repo.set_campaign_status('u', campaign['id'], 'sending')


def test_common_delivery_guard_runs_before_mail_provider_even_without_lead(monkeypatch):
    repo, _, _ = setup_campaign([GOOD])
    monkeypatch.setattr(sending, 'send_hostinger_message', lambda **kwargs: pytest.fail('Must not deliver'))
    with pytest.raises(OutreachSafetyError):
        sending.send_with_sender(repo, user_id='u', sender_id='not-even-read', to_email='sales@revenuebase.ai', subject='For ' + TITLE, body='Hi there,')


def test_worker_holds_unsafe_legacy_queue_without_disconnecting_sender(monkeypatch):
    repo, data, leads = setup_campaign([GOOD])
    campaign, _, _, _ = repo.create_campaign('u', data, leads)
    repo.approve_campaign('u', campaign['id'])
    repo.database.execute('UPDATE email_messages SET body=?', ('Hi ' + TITLE + ' team,',), False)
    monkeypatch.setattr(worker, 'get_outreach_repository', lambda: repo)
    monkeypatch.setattr(worker, '_can_send_now', lambda *a: (True, None))
    monkeypatch.setattr(sending, 'send_hostinger_message', lambda **kwargs: pytest.fail('Must not deliver'))
    assert worker.process_once() == 1
    row = repo.database.execute('SELECT status,last_error FROM email_messages').rows[0]
    assert row['status'] == 'failed' and 'Outreach held' in row['last_error']
    assert repo.get_sender('u', data.sender_id)['status'] == 'connected'


def test_saved_legacy_directory_is_flagged_and_generic_quick_send_still_held():
    from app.leads.repository import LeadRepository
    from app.leads.parser import ParsedLead
    repo, _, _ = setup_campaign([GOOD])
    leads = LeadRepository(repo.database)
    lead_list = leads.create_lead_list('u', 'solar', 'London', 1)
    saved, _, _ = leads.import_parsed_leads('u', lead_list['id'], [ParsedLead(company_name=TITLE, email='sales@revenuebase.ai', website='https://revenuebase.ai')])
    raw = repo.database.execute('SELECT company_name FROM leads').rows[0]
    assert raw['company_name'] == TITLE  # Retain provenance, never save vendor as prospect.
    row = leads.get_leads_by_ids('u', [saved[0]['id']])[0]
    assert row['outreach_block_reason'] and row['company_name'] is None
    with pytest.raises(OutreachSafetyError, match='Directory'):
        repo.assert_outgoing_safe('u', 'sales@revenuebase.ai', 'Hello', 'Hi there,')
    # Tenant-isolated evidence: another user's records do not block this user.
    repo.assert_outgoing_safe('different-user', 'sales@revenuebase.ai', 'Hello', 'Hi there,')


def test_unknown_or_mismatched_website_evidence_does_not_spend_ai_credits():
    from app.outreach.personalization import CompanyNamePreparer
    class Never:
        def connected_credentials(self, *args): pytest.fail('Must not use AI to name a directory operator')
        def company_name(self, *args): pytest.fail('Must not crawl a known unsafe recipient')
    results = CompanyNamePreparer(Never(), crawler=Never()).prepare('u', [BAD, {**GOOD, 'email': 'other@other.test'}])
    assert all(row['outreach_block_reason'] and row['company_name'] is None for row in results)
