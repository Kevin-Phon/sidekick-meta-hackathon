import json
import httpx
from app.repository import Repository
from app.model import MetaClient
from app.preparation import prepare


def test_clean_workspace_preserves_archive_and_scopes_new_imports(tmp_path):
    repo=Repository(tmp_path/'workspace.db')
    repo.import_items([{'provider_id':'a','title':'Old example','body':'Archived','kind':'assignment'}])
    prepare(repo)
    old=repo.snapshot()['sources'][0]
    workspace=repo.create_workspace('My workspace')
    assert repo.snapshot()['sources']==[] and repo.snapshot()['drafts']==[] and repo.snapshot()['tasks']==[]
    assert len(repo.records('sources'))==1
    repo.import_items([{'provider_id':'a','title':'Uploaded assignment','body':'New material','kind':'assignment'}])
    current=repo.snapshot()['sources'][0]
    assert current['id']!=old['id']
    prepare(repo)
    assert all(r['id']==current['id'] for d in repo.snapshot()['drafts'] for r in d['source_refs'])
    repo.update_profile({'active_workspace':'legacy'})
    assert [s['title'] for s in repo.snapshot()['sources']]==['Old example']
    repo.update_profile({'active_workspace':workspace['id']})
    assert [s['title'] for s in Repository(repo.path).snapshot()['sources']]==['Uploaded assignment']


def test_mail_generation_and_plan_prepare_reviewable_reply():
    source={'id':'m1','revision':1,'title':'Team update','kind':'mail','body':'Please send an update before our project meeting.','metadata':{}}
    def serve(request):
        payload=json.loads(request.content)
        if payload['response_format']['json_schema']['name']=='sidekick_plan':
            data={'summary':'Prepare a reply for review.','priorities':[{'source_id':'m1','reason':'The team requested a project update.'}],'actions':[{'source_id':'m1'}]}
        else:
            data={'kind':'mail_reply','markdown':'## Suggested reply\nThanks. I will prepare an update.\n\nReview before sending.','source_refs':[{'id':'m1','revision':1}],'missing_information':[]}
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(data)}}]})
    client=MetaClient('fake',transport=httpx.MockTransport(serve))
    assert client.plan([source],[],[])['actions']==[{'source_id':'m1'}]
    assert client.generate([source])['kind']=='mail_reply'


def test_workspace_api_isolates_source_consent_and_history(tmp_path):
    from test_api import connected
    c=connected(tmp_path)
    c.post('/api/demo')
    old=c.get('/api/state').json()['sources'][0]
    assert c.post('/api/workspaces',json={'name':'Fresh start'}).status_code==200
    state=c.get('/api/state').json()
    assert state['sources']==[] and state['agent_runs']==[]
    assert any(w['id']=='legacy' for w in state['workspaces'])
    c.post('/api/model/key',json={'key':'test'})
    result=c.post('/api/agent/run',json={'source_ids':[old['id']],'source_revisions':{old['id']:1},'source_hashes':{old['id']:old['content_hash']},'consent':True})
    assert result.status_code==400


def test_workspace_preparation_history_prevents_repeated_catchup(tmp_path):
    from app.scheduler import should_catch_up
    from datetime import datetime,timezone
    repo=Repository(tmp_path/'workspace.db')
    prepare(repo)
    legacy=repo.snapshot()['checks'][0]
    workspace=repo.create_workspace('Clean')
    assert repo.snapshot()['checks']==[]
    result=prepare(repo)
    checks=repo.snapshot()['checks']
    assert len(checks)==1 and checks[0]['finished_at']==result['checked_at']
    assert not should_catch_up(datetime.now(timezone.utc),checks[-1]['finished_at'])
    repo.update_profile({'active_workspace':'legacy'})
    assert [c['id'] for c in repo.snapshot()['checks']]==[legacy['id']]


def test_new_install_has_no_prefilled_personal_profile(tmp_path):
    profile=Repository(tmp_path/'fresh.db').snapshot()['profile']
    assert profile['name']=='' and profile['goal']==''


def test_malformed_workspace_selection_is_rejected_cleanly(tmp_path):
    import pytest
    repo=Repository(tmp_path/'workspace.db')
    for value in ([], {}, 12):
        with pytest.raises(ValueError,match='workspace'):
            repo.update_profile({'active_workspace':value})
