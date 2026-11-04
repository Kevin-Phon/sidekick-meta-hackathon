import json
from urllib.parse import urlparse,parse_qs
import httpx
from app.main import create_app
from app.config import Settings
from fastapi.testclient import TestClient

CLIENT={'web':{'client_id':'123-test.apps.googleusercontent.com','client_secret':'fake-google-secret','redirect_uris':['http://127.0.0.1:8765/oauth/google/callback']}}
SCOPE='https://www.googleapis.com/auth/gmail.readonly'

def client(tmp_path):
    c=TestClient(create_app(Settings(data_dir=tmp_path)))
    boot=c.get('/api/bootstrap');c.headers.update({'X-Sidekick-Token':boot.json()['token'],'Origin':'http://testserver'})
    return c

def start(c):
    assert c.post('/api/gmail/configure',json=CLIENT).status_code==200
    response=c.post('/api/gmail/start')
    assert response.status_code==200
    return parse_qs(urlparse(response.json()['authorization_url']).query)

def test_gmail_requires_configuration_and_builds_real_readonly_auth_url(tmp_path):
    c=client(tmp_path)
    assert c.post('/api/gmail/start').status_code==409
    q=start(c)
    assert q['scope']==[SCOPE]
    assert q['redirect_uri']==CLIENT['web']['redirect_uris']
    assert q['code_challenge_method']==['S256'] and q['code_challenge'][0]
    assert 'client_secret' not in q
    assert c.get('/api/gmail/status').json()['connected'] is False
    assert 'fake-google-secret' not in c.get('/api/state').text

def test_callback_needs_its_own_browser_cookie_and_single_use_state(tmp_path,monkeypatch):
    from app.gmail import GmailConnection
    calls=[]
    def serve(req):
        calls.append(req)
        if str(req.url).endswith('/token'):
            values=parse_qs(req.content.decode());assert values['code_verifier'][0]
            return httpx.Response(200,json={'access_token':'fake-access-token','expires_in':3600,'scope':SCOPE})
        return httpx.Response(200,json={'emailAddress':'fictional@example.test'})
    monkeypatch.setattr(GmailConnection,'transport',httpx.MockTransport(serve))
    c=client(tmp_path);q=start(c);state=q['state'][0]
    bad=TestClient(c.app)
    assert bad.get('/oauth/google/callback',params={'state':state,'code':'test'},follow_redirects=False).status_code==400
    # Google redirects don't send the app's Strict cookie; dedicated flow cookie authenticates callback.
    c.cookies.delete('sidekick_session')
    result=c.get('/oauth/google/callback',params={'state':state,'code':'test'},follow_redirects=False)
    assert result.status_code==303 and result.headers['location']=='/?gmail=connected'
    assert len(calls)==2
    assert c.get('/oauth/google/callback',params={'state':state,'code':'test'},follow_redirects=False).status_code==400
    boot=c.get('/api/bootstrap');c.headers['X-Sidekick-Token']=boot.json()['token']
    status=c.get('/api/gmail/status').json()
    assert status['connected'] and status['email']=='fictional@example.test'
    assert 'fake-access-token' not in c.get('/api/state').text
    for p in tmp_path.iterdir():
        if p.is_file():assert b'fake-access-token' not in p.read_bytes() and b'fake-google-secret' not in p.read_bytes()
    c.post('/api/workspaces',json={'name':'Another workspace'})
    assert c.get('/api/gmail/status').json()['connected'] is False

def test_gmail_rejects_invalid_client_and_provider_errors_are_sanitized(tmp_path,monkeypatch):
    from app.gmail import GmailConnection
    c=client(tmp_path)
    for payload in ({}, {'web':{**CLIENT['web'],'redirect_uris':None}}, {'web':{**CLIENT['web'],'client_id':'https://evil.test'}}, {'web':{**CLIENT['web'],'redirect_uris':['https://evil.test']}}):
        assert c.post('/api/gmail/configure',json=payload).status_code==400
    monkeypatch.setattr(GmailConnection,'transport',httpx.MockTransport(lambda req:httpx.Response(400,json={'error':'fake-access-token fake-google-secret'})))
    q=start(c)
    result=c.get('/oauth/google/callback',params={'state':q['state'][0],'code':'test'},follow_redirects=False)
    assert result.headers['location']=='/?gmail=failed'
    assert c.get('/api/gmail/status').json()['connected'] is False

def test_expired_denied_and_wrong_workspace_flows_do_not_exchange_tokens(monkeypatch):
    import pytest
    from app.gmail import GmailConnection
    g=GmailConnection();g.configure(CLIENT)
    monkeypatch.setattr(g,'_json',lambda *a,**kw:pytest.fail('Should not exchange a token'))
    url,cookie=g.start('workspace-a');state=parse_qs(urlparse(url).query)['state'][0]
    assert g.finish(state,cookie,'','access_denied','workspace-a') is False
    with pytest.raises(ValueError):g.finish(state,cookie,'code','','workspace-a')
    url,cookie=g.start('workspace-a');state=parse_qs(urlparse(url).query)['state'][0]
    g.pending[state]['expires']=0
    with pytest.raises(ValueError):g.finish(state,cookie,'code','','workspace-a')
    url,cookie=g.start('workspace-a');state=parse_qs(urlparse(url).query)['state'][0]
    with pytest.raises(ValueError):g.finish(state,cookie,'code','','workspace-b')

def test_broader_permission_grant_is_not_accepted(monkeypatch):
    import pytest
    from app.gmail import GmailConnection,GmailError
    g=GmailConnection();g.configure(CLIENT)
    monkeypatch.setattr(g,'_json',lambda *a,**kw:{'access_token':'fake','expires_in':3600,'scope':SCOPE+' https://mail.google.com/'})
    url,cookie=g.start('legacy');state=parse_qs(urlparse(url).query)['state'][0]
    with pytest.raises(GmailError):g.finish(state,cookie,'code','','legacy')
    assert not g.status('legacy')['connected']

def test_callback_credentials_are_omitted_from_access_logs():
    import logging
    from app.gmail import CallbackLogFilter
    filtered=CallbackLogFilter()
    record=logging.LogRecord('uvicorn.access',20,'',1,'%s - "%s %s HTTP/%s" %d',('localhost','GET','/oauth/google/callback?code=fake-secret','1.1',303),None)
    assert filtered.filter(record) is False
    record.args=('localhost','GET','/api/state','1.1',200)
    assert filtered.filter(record) is True

def test_expired_connection_can_start_a_fresh_signin():
    from app.gmail import GmailConnection
    g=GmailConnection();g.configure(CLIENT)
    g.account={'workspace':'legacy','expires_at':0,'email':'expired@example.test','token':'expired'}
    url,_=g.start('legacy')
    assert url.startswith('https://accounts.google.com/')

def test_start_from_localhost_requires_canonical_callback_host(tmp_path):
    c=client(tmp_path);assert c.post('/api/gmail/configure',json=CLIENT).status_code==200
    c.get('http://localhost:8765/api/bootstrap')
    result=c.post('http://localhost:8765/api/gmail/start',headers={'Origin':'http://localhost:8765'})
    assert result.status_code==409
    assert '127.0.0.1:8765' in result.json()['detail']

def test_successful_callback_invalidates_other_pending_signins(monkeypatch):
    import pytest
    from app.gmail import GmailConnection
    g=GmailConnection();g.configure(CLIENT)
    def exchange(method,url,**kwargs):
        return {'access_token':'fake','expires_in':3600,'scope':SCOPE} if method=='POST' else {'emailAddress':'first@example.test'}
    monkeypatch.setattr(g,'_json',exchange)
    first,c1=g.start('one');second,c2=g.start('two')
    s1=parse_qs(urlparse(first).query)['state'][0];s2=parse_qs(urlparse(second).query)['state'][0]
    assert g.finish(s1,c1,'code','','one') is True
    with pytest.raises(ValueError):g.finish(s2,c2,'code','','two')
    assert g.status('one')['email']=='first@example.test'
    assert not g.status('two')['connected']
