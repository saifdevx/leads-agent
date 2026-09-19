import pathlib
import sqlite3
from cryptography.fernet import Fernet
from app.outreach.repository import OutreachRepository
from app.outreach.schemas import TemplateCreate, CampaignCreate
from app.providers.security import CredentialCipher

class Result:
    def __init__(self, affected, rows): self.affected_row_count=affected; self.rows=rows

class SqliteAdapter:
    def __init__(self):
        self.conn=sqlite3.connect(':memory:'); self.conn.row_factory=sqlite3.Row
        root=pathlib.Path(__file__).resolve().parents[1]
        for file in sorted((root/'migrations').glob('*.sql')): self.conn.executescript(file.read_text())
    def execute(self,sql,params=(),want_rows=True):
        cur=self.conn.execute(sql,params); self.conn.commit()
        rows=[dict(r) for r in cur.fetchall()] if want_rows else []
        return Result(cur.rowcount if cur.rowcount!=-1 else 0, rows)
    def execute_batch(self,statements): return [self.execute(sql,params,want) for sql,params,want in statements]

class Leads:
    def get_leads_by_ids(self,user_id,ids):
        return [{'id':'lead-1','company_name':'Acme Solar','first_name':'Sam','last_name':'Lee','job_title':'Owner','email':'sam@acme.test','website':'https://acme.test','domain':'acme.test','city':'Dallas','region':'Texas','country':'USA'}]

def test_campaign_creation_renders_and_queues_only_after_approval():
    repo=OutreachRepository(SqliteAdapter(), CredentialCipher(Fernet.generate_key().decode()))
    template=repo.save_template('u',TemplateCreate(name='Intro',category='General',subject='Hi {{company_name}}',body='Hello {{first_name}} from {{sender_name}}'))
    sender=repo.save_gmail_sender('u','sender@example.com','Sender Name',{'access_token':'a','refresh_token':'r','expires_at':'2099-01-01T00:00:00+00:00'})
    campaign,preview,_,_=repo.create_campaign('u',CampaignCreate(name='Test Campaign',lead_ids=['lead-1'],template_id=template['id'],sender_id=sender['id']),Leads())
    assert campaign['status']=='draft'
    assert preview[0]['subject']=='Hi Acme Solar'
    assert 'Hello Sam from Sender Name' in preview[0]['body']
    assert repo.due_messages()==[]
    repo.approve_campaign('u',campaign['id'])
    assert len(repo.due_messages())==1
