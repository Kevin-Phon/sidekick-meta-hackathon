import base64
import time
import httpx
import pytest
from app.gmail import GmailConnection,GmailError

def encoded(text):return base64.urlsafe_b64encode(text.encode()).decode().rstrip('=')

def ready(transport):
    g=GmailConnection();g.transport=transport
    g.account={'token':'fake-access','email':'reader@example.test','workspace':'legacy','expires_at':time.time()+3600}
    return g

def test_recent_import_only_reads_five_inbox_messages_and_uses_plain_body():
    calls=[]
    def serve(req):
        calls.append(req);assert req.method=='GET'
        if req.url.path.endswith('/messages'):
            assert req.url.params['maxResults']=='5' and req.url.params['labelIds']=='INBOX'
            return httpx.Response(200,json={'messages':[{'id':str(i)} for i in range(7)]})
        return httpx.Response(200,json={'id':req.url.path.rsplit('/',1)[-1],'internalDate':'1793800000000','labelIds':['INBOX','IMPORTANT'],
            'snippet':'A small preview','payload':{'headers':[{'name':'Subject','value':'Team meeting'},{'name':'From','value':'Alex <alex@example.test>'}],
            'parts':[{'mimeType':'text/html','body':{'data':encoded('<b>HTML alternative</b>')}},{'mimeType':'text/plain','body':{'data':encoded('Please review the agenda.')}},{'filename':'private.txt','mimeType':'text/plain','body':{'data':encoded('ATTACHMENT SECRET')}}]}})
    g=ready(httpx.MockTransport(serve));result=g.recent('legacy')
    assert len(result['items'])==5 and len(calls)==6
    item=result['items'][0]
    assert 'Please review the agenda.' in item['body'] and 'ATTACHMENT SECRET' not in item['body'] and 'HTML alternative' not in item['body']
    assert item['metadata']['gmail_important'] is True
    assert item['metadata']['sender']=='Alex <alex@example.test>'
    assert 'fake-access' not in str(result)
    assert result['items'][0]['provider_id']=='0'

def test_html_has_no_active_content_and_invalid_messages_are_skipped():
    def serve(req):
        if req.url.path.endswith('/messages'):return httpx.Response(200,json={'messages':[{'id':'one'},{'id':'two'}]})
        if req.url.path.endswith('/two'):return httpx.Response(404,json={})
        return httpx.Response(200,json={'id':'one','payload':{'mimeType':'text/html','body':{'data':encoded('<style>hidden secret</style><p>Hello &amp; welcome</p><script>trackingSecret()</script><img src="https://evil.test/tracker">')}}})
    result=ready(httpx.MockTransport(serve)).recent('legacy')
    assert len(result['items'])==1 and result['skipped_count']==1
    assert 'Hello & welcome' in result['items'][0]['body']
    assert all(x not in result['items'][0]['body'] for x in ('trackingSecret','hidden secret','evil.test'))

@pytest.mark.parametrize('workspace,expiry',[('different',3600),('legacy',-1)])
def test_wrong_workspace_or_expired_connection_never_reads_mail(workspace,expiry):
    g=ready(httpx.MockTransport(lambda req:pytest.fail('No provider call expected')))
    g.account['expires_at']=time.time()+expiry
    with pytest.raises(GmailError):g.recent(workspace)

def test_import_endpoint_requires_consent_and_saves_idempotent_snapshots(tmp_path,monkeypatch):
    from test_gmail import client
    calls=[]
    def recent(self,workspace):
        calls.append(workspace)
        return {'items':[{'connection_id':'gmail:mailbox','provider_id':'one','kind':'mail','title':'Project meeting','body':'Review the agenda.','metadata':{'provider':'gmail'}}],'skipped_count':0}
    monkeypatch.setattr(GmailConnection,'recent',recent)
    c=client(tmp_path)
    assert c.post('/api/gmail/import',json={}).status_code==400
    assert not calls
    result=c.post('/api/gmail/import',json={'consent':True})
    assert result.status_code==200 and result.json()['fetched_count']==1
    assert result.json()['new_count']==1
    assert c.post('/api/gmail/import',json={'consent':True}).json()['new_count']==0
    saved=c.get('/api/state').json()
    assert len(saved['sources'])==1 and not saved['drafts'] and not saved['agent_runs']

def test_import_cannot_save_into_a_workspace_changed_after_approval(tmp_path):
    from app.repository import Repository
    repo=Repository(tmp_path/'sidekick.db')
    repo.create_workspace('Other')
    with pytest.raises(ValueError,match='workspace'):
        repo.import_items([{'title':'Private mail','kind':'mail','body':'private'}],expected_workspace='legacy')
    assert not repo.snapshot()['sources']

def test_unnamed_text_attachments_are_excluded_and_unknown_dates_stay_unknown():
    from app.gmail_messages import snapshot
    item=snapshot({'id':'one','payload':{'parts':[{'mimeType':'text/plain','body':{'data':encoded('Main body')}},{'mimeType':'text/plain','headers':[{'name':'Content-Disposition','value':'attachment'}],'body':{'data':encoded('UNNAMED SECRET')}}]}},'reader@example.test')
    assert 'UNNAMED SECRET' not in item['body']
    assert item['metadata']['received_at']==''

def test_blank_subject_uses_a_display_fallback():
    from app.gmail_messages import snapshot
    item=snapshot({'id':'one','payload':{'headers':[{'name':'Subject','value':'   '}],'mimeType':'text/plain','body':{'data':encoded('Body')}}},'reader@example.test')
    assert item['title']=='(No subject)'
