import json
import pytest
import httpx
from app.repository import Repository
from app.model import MetaClient, ModelError


def setup(tmp_path):
    repo = Repository(tmp_path / 'agent.db')
    repo.import_items([
        {'provider_id': 'school', 'kind': 'lecture', 'title': 'Sets', 'body': 'Intersection means both.'},
        {'provider_id': 'project', 'kind': 'project_note', 'title': 'Demo meeting', 'body': 'Completed import. Blocked on tests.'}])
    return repo


class FakeModel:
    def __init__(self):
        self.calls = 0
    def plan(self, sources, tasks, changes):
        self.calls += 1
        self.changes = changes
        return {'summary': 'Prepare school and project work.', 'priorities': [
            {'source_id': s['id'], 'reason': 'Review source before meeting.'} for s in sources],
            'actions': [{'source_id': s['id']} for s in sources if not any(t['source_id'] == s['id'] and t['status'] != 'open' for t in tasks)][:2]}
    def generate(self, sources):
        self.calls += 1
        s = sources[0]
        return {'kind': 'meeting_brief' if s['kind'] == 'project_note' else 'study_guide',
                'markdown': 'Prepared from ' + s['body'], 'source_refs': [{'id': s['id'], 'revision': s['revision']}],
                'status': 'review_needed', 'provider': 'meta', 'model': 'muse-spark-1.3'}


def test_agent_remembers_changes_and_skips_identical_runs(tmp_path):
    from app.agent import AgentRunner
    repo, client = setup(tmp_path), FakeModel()
    run = AgentRunner(repo, client).run(repo.snapshot()['sources'])
    assert run['status'] == 'completed' and len(run['draft_ids']) == 2
    assert client.calls == 3
    assert AgentRunner(Repository(repo.path), client).run(repo.snapshot()['sources'])['status'] == 'unchanged'
    assert client.calls == 3
    repo.import_items([{'provider_id': 'school', 'kind': 'lecture', 'title': 'Sets', 'body': 'Union means either.'}])
    run = AgentRunner(repo, client).run(repo.snapshot()['sources'])
    assert any(c['kind'] == 'changed' and c['before']['revision'] == 1 and c['after']['revision'] == 2 for c in run['changes'])
    task = repo.snapshot()['tasks'][0]
    repo.update_task(task['id'], {'status': 'done'})
    run = AgentRunner(repo, client).run(repo.snapshot()['sources'])
    assert any(c['kind'] == 'progress' for c in run['changes'])
    assert repo.snapshot()['tasks'][0]['status'] == 'done'


def test_agent_source_or_progress_race_does_not_commit_outputs(tmp_path):
    from app.agent import AgentRunner
    for mutate in ('source', 'progress'):
        repo, client = setup(tmp_path / mutate), FakeModel()
        original = client.generate
        def generate(sources):
            if mutate == 'source':
                repo.import_items([{'provider_id': 'school', 'kind': 'lecture', 'title': 'Sets', 'body': 'New private text'}])
            else:
                repo.update_task(repo.snapshot()['tasks'][0]['id'], {'status': 'done'})
            return original(sources)
        client.generate = generate
        with pytest.raises(ValueError, match='changed'):
            AgentRunner(repo, client).run(repo.snapshot()['sources'])
        assert repo.records('drafts') == []
        assert not any(r['status'] == 'completed' for r in repo.records('agent_runs'))


def test_failed_run_visible_and_never_advances_checkpoint(tmp_path):
    from app.agent import AgentRunner
    repo, client = setup(tmp_path), FakeModel()
    def fail(*args):
        raise ModelError('Meta request timed out. Check usage.')
    client.plan = fail
    with pytest.raises(ModelError):
        AgentRunner(repo, client).run(repo.snapshot()['sources'])
    assert repo.records('agent_runs')[-1]['status'] == 'failed'
    assert repo.records('agent_checkpoints') == []


def test_meta_planner_rejects_unknown_and_completed_actions():
    source = {'id': 's1', 'revision': 1, 'content_hash': 'h', 'kind': 'project_note', 'title': 'Meeting', 'body': 'Prepare update', 'metadata': {}, 'due_at': None}
    def serve(request):
        payload = json.loads(request.content)
        assert payload['response_format']['json_schema']['name'] == 'sidekick_plan'
        assert 'tools' not in payload
        plan = {'summary': 'Prepare', 'priorities': [{'source_id': 's1', 'reason': 'Meeting'}], 'actions': [{'source_id': 'unknown'}]}
        return httpx.Response(200, json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(plan)}}]})
    with pytest.raises(ModelError):
        MetaClient('test', transport=httpx.MockTransport(serve)).plan([source], [], [])
    def completed(request):
        plan = {'summary': 'Prepare', 'priorities': [], 'actions': [{'source_id': 's1'}]}
        return httpx.Response(200, json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(plan)}}]})
    with pytest.raises(ModelError):
        MetaClient('test', transport=httpx.MockTransport(completed)).plan([source], [{'source_id':'s1','status':'done'}], [])


def test_agent_api_requires_exact_scope_consent_and_skips_duplicates(tmp_path, monkeypatch):
    from test_api import connected
    from app.model import MetaClient
    c = connected(tmp_path)
    assert c.post('/api/agent/demo?stage=initial').status_code == 200
    c.post('/api/model/key', json={'key':'test-only'})
    sources = c.get('/api/state').json()['sources']
    selected = [s for s in sources if s['connection_id'] == 'agent-demo']
    assert len(selected) == 4
    packet = {'source_ids':[s['id'] for s in selected], 'source_revisions':{s['id']:s['revision'] for s in selected},
              'source_hashes':{s['id']:s['content_hash'] for s in selected}, 'consent':True}
    assert c.post('/api/agent/run', json={**packet,'consent':False}).status_code == 400
    assert c.post('/api/agent/run', json={**packet,'source_hashes':{}}).status_code == 400
    fake = FakeModel()
    monkeypatch.setattr(MetaClient, 'plan', lambda self,*args: fake.plan(*args))
    monkeypatch.setattr(MetaClient, 'generate', lambda self,*args: fake.generate(*args))
    assert c.post('/api/agent/run', json=packet).json()['status'] == 'completed'
    assert c.post('/api/agent/run', json=packet).json()['status'] == 'unchanged'
    assert fake.calls == 3
    assert c.get('/api/state').json()['agent_runs'][-1]['status'] == 'completed'
    c.post('/api/agent/demo?stage=update')
    assert c.post('/api/agent/run', json=packet).status_code == 400
    assert c.get('/api/state').json()['agent_runs'][-1]['stale'] is True
    assert c.post('/api/model/key', json={'key':''}).status_code == 200
    assert c.post('/api/agent/run', json=packet).status_code == 409


def test_historical_private_title_is_not_transmitted():
    from app.agent import model_changes
    delta = [{'kind':'changed','source_id':'s','before':{'title':'Withdrawn private title','body':'Old private text','due_at':'old','revision':1,'content_hash':'old'},
              'after':{'title':'Current approved title','revision':2,'content_hash':'new'}}]
    assert 'Withdrawn private title' not in json.dumps(model_changes(delta))


def test_selected_mail_requirement_reaches_preparation(tmp_path):
    from app.agent import AgentRunner
    repo = setup(tmp_path)
    repo.import_items([{'provider_id':'mail','kind':'mail','title':'Meeting update','body':'Bring the orange error-state slide.'}])
    client = FakeModel()
    original = client.generate
    seen=[]
    def generate(sources):
        seen.append([s['body'] for s in sources])
        return original(sources)
    client.generate = generate
    AgentRunner(repo, client).run(repo.snapshot()['sources'])
    assert all('Bring the orange error-state slide.' in packet for packet in seen)


@pytest.mark.parametrize('choice', ['unexpected', None, 3, {'message': []}])
def test_malformed_provider_choice_is_safe_model_error(choice):
    source={'id':'s1','revision':1,'kind':'lecture','title':'Notes','body':'Facts','metadata':{}}
    transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'choices':[choice]}))
    with pytest.raises(ModelError):
        MetaClient('test',transport=transport).plan([source],[],[])
    with pytest.raises(ModelError):
        MetaClient('test',transport=transport).generate([source])


def test_deleting_source_removes_its_agent_memory_and_history(tmp_path):
    from app.agent import AgentRunner
    repo=setup(tmp_path)
    sources=repo.snapshot()['sources']
    AgentRunner(repo,FakeModel()).run(sources)
    repo.delete_source(sources[0]['id'])
    assert repo.records('agent_checkpoints') == []
    assert repo.records('agent_runs') == []
