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
    assert len(state['drafts']) == 3
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
