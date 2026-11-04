from fastapi.testclient import TestClient
from app.main import create_app
from app.config import Settings


def connected(tmp_path):
    c = TestClient(create_app(Settings(data_dir=tmp_path)))
    boot = c.get('/api/bootstrap')
    c.headers['X-Sidekick-Token'] = boot.json()['token']
    c.headers['Origin'] = 'http://testserver'
    return c


def test_mutation_requires_session_and_origin(tmp_path):
    c = TestClient(create_app(Settings(data_dir=tmp_path)))
    assert c.post('/api/demo').status_code == 403
    c = connected(tmp_path)
    assert c.post('/api/demo', headers={'Origin': 'https://evil.example'}).status_code == 403
    assert c.get('/api/state', headers={'Host': 'evil.example'}).status_code == 400


def test_full_demo_cycle_and_download(tmp_path):
    c = connected(tmp_path)
    assert c.post('/api/demo').status_code == 200
    state = c.get('/api/state').json()
    assert len(state['sources']) == 5
    assert len(state['drafts']) == 4
    assert any(d['kind'] == 'mail_reply' for d in state['drafts'])
    assert c.post('/api/checks').json()['draft_count'] == 0
    task = state['tasks'][0]
    assert c.patch('/api/tasks/' + task['id'], json={'status': 'done'}).status_code == 200
    assert c.get('/api/state').json()['tasks'][0]['status'] == 'done'
    draft = next(d for d in state['drafts'] if d['kind'] == 'homework')
    response = c.get('/api/drafts/' + draft['id'] + '/download')
    assert 'A ∩ B = {3, 4}' in response.text
    assert response.headers['content-type'].startswith('text/markdown')
    assert all(x['status'] != 'connected' for x in state['connections'])


def test_import_validation_and_missing_ai_are_visible(tmp_path):
    c = connected(tmp_path)
    assert c.post('/api/import', json={'items': [{'title': 'My lecture', 'kind': 'lecture', 'body': 'Real course notes'}]}).status_code == 200
    assert c.post('/api/import', json={'items': [{'title': '', 'body': 'bad'}]}).status_code == 400
    draft = c.get('/api/state').json()['drafts'][0]
    assert draft['provider'] == 'source_outline'
    assert c.post('/api/model/generate').status_code == 409
    assert c.post('/api/import/file?filename=program.exe&kind=lecture', content=b'no').status_code == 400


def test_single_source_delete_and_profile_persist(tmp_path):
    c = connected(tmp_path)
    c.post('/api/demo')
    state = c.get('/api/state').json()
    note = next(x for x in state['sources'] if x['kind'] == 'project_note')
    assert c.delete('/api/sources/' + note['id']).status_code == 200
    assert len(c.get('/api/state').json()['sources']) == 4
    assert c.patch('/api/profile', json={'goal': 'Review my notes', 'daily_enabled': True}).status_code == 200
    assert connected(tmp_path).get('/api/state').json()['profile']['daily_enabled'] is True


def test_bad_shapes_and_metadata_rejected_before_saving(tmp_path):
    c = connected(tmp_path)
    for item in [7, {'title': 'Bad', 'kind': 'assignment', 'body': 'Q', 'metadata': {'missing_sources': [1]}}]:
        assert c.post('/api/import', json={'items': [item]}).status_code == 400
    assert c.get('/api/state').json()['sources'] == []
    assert c.post('/api/checks').status_code == 200


def test_same_filename_distinct_content_keeps_separate_tasks(tmp_path):
    c = connected(tmp_path)
    url = '/api/import/file?filename=assignment.md&kind=assignment'
    c.post(url + '&course=CS1', content=b'First problem')
    task = c.get('/api/state').json()['tasks'][0]
    c.patch('/api/tasks/' + task['id'], json={'status': 'done'})
    c.post(url + '&course=CS2', content=b'Second problem')
    state = c.get('/api/state').json()
    assert len(state['sources']) == 2
    assert sorted(t['status'] for t in state['tasks']) == ['done', 'open']


def test_source_update_invalidates_obsolete_drafts(tmp_path):
    c = connected(tmp_path)
    for body in ['Old facts', 'Changed facts']:
        c.post('/api/import', json={'items': [{'provider_id': 'same', 'title': 'Notes', 'body': body}]})
    state = c.get('/api/state').json()
    assert len(state['drafts']) == 1
    assert state['drafts'][0]['source_refs'][0]['revision'] == 2
    export = c.get('/api/drafts/' + state['drafts'][0]['id'] + '/download').text
    assert 'source_outline' in export and 'revision 2' in export


def test_key_stays_in_memory_and_generation_requires_selected_source_consent(tmp_path, monkeypatch):
    from app.model import MetaClient
    monkeypatch.delenv('MODEL_API_KEY', raising=False)
    c = connected(tmp_path)
    assert c.post('/api/model/key', json={'key': 'test-secret'}).status_code == 200
    state = c.get('/api/state').json()
    assert 'test-secret' not in str(state)
    assert state['model']['configured'] is True and state['model']['verified'] is False
    c.post('/api/demo')
    source = next(s for s in c.get('/api/state').json()['sources'] if s['kind'] == 'lecture')
    assert c.post('/api/model/generate', json={'source_ids': [source['id']]}).status_code == 400
    def generate(self, sources):
        assert len(sources) == 1
        return {'kind': 'study_guide', 'markdown': '## Key ideas\nVerified transport test', 'source_refs': [{'id': source['id'], 'revision': 1}], 'provider': 'meta', 'model': 'muse-spark-1.3', 'status': 'review_needed'}
    monkeypatch.setattr(MetaClient, 'generate', generate)
    result = c.post('/api/model/generate', json={'source_ids': [source['id']], 'source_revisions': {source['id']: 1}, 'source_hashes': {source['id']: source['content_hash']}, 'consent': True})
    assert result.status_code == 200
    saved = c.get('/api/state').json()
    assert saved['model']['verified'] is True
    assert any(d['provider'] == 'meta' for d in saved['drafts'])
    assert 'test-secret' not in (tmp_path / 'sidekick.db').read_bytes().decode('latin1')
    assert connected(tmp_path).get('/api/state').json()['model']['configured'] is False
    assert c.post('/api/model/key', json={'key': ''}).status_code == 200
    assert c.get('/api/state').json()['model']['configured'] is False


def test_source_consent_is_bound_to_the_previewed_revision(tmp_path, monkeypatch):
    from app.model import MetaClient
    monkeypatch.delenv('MODEL_API_KEY', raising=False)
    c = connected(tmp_path)
    c.post('/api/model/key', json={'key': 'test'})
    c.post('/api/import', json={'items': [{'provider_id': 'same', 'title': 'Lecture', 'body': 'Originally approved'}]})
    original = c.get('/api/state').json()['sources'][0]
    c.post('/api/import', json={'items': [{'provider_id': 'same', 'title': 'Lecture', 'body': 'Private new material'}]})
    calls = []
    monkeypatch.setattr(MetaClient, 'generate', lambda self, sources: calls.append(sources))
    result = c.post('/api/model/generate', json={'source_ids': [original['id']], 'source_revisions': {original['id']: 1}, 'consent': True})
    assert result.status_code == 400
    assert calls == []


def test_deleted_and_recreated_source_does_not_reuse_old_approval(tmp_path, monkeypatch):
    from app.model import MetaClient
    c = connected(tmp_path)
    c.post('/api/model/key', json={'key': 'test'})
    c.post('/api/import', json={'items': [{'provider_id': 'same', 'title': 'Lecture', 'body': 'Originally approved'}]})
    original = c.get('/api/state').json()['sources'][0]
    c.delete('/api/sources/' + original['id'])
    c.post('/api/import', json={'items': [{'provider_id': 'same', 'title': 'Lecture', 'body': 'Private replacement'}]})
    calls = []
    def generate(self, sources):
        calls.append(sources)
        return {'kind': 'study_guide', 'markdown': 'test', 'source_refs': [{'id': original['id'], 'revision': 1}], 'provider': 'meta', 'model': 'muse-spark-1.3', 'status': 'review_needed'}
    monkeypatch.setattr(MetaClient, 'generate', generate)
    result = c.post('/api/model/generate', json={'source_ids': [original['id']], 'source_revisions': {original['id']: 1}, 'source_hashes': {original['id']: original['content_hash']}, 'consent': True})
    assert result.status_code == 400
    assert calls == []
