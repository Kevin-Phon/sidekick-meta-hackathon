from app.repository import Repository


def test_reimport_is_idempotent_and_revision_preserves_done(tmp_path):
    repo = Repository(tmp_path / 'test.db')
    item = {'provider_id': 'hw1', 'connection_id': 'imports', 'kind': 'assignment', 'title': 'Sets', 'body': 'Q1', 'metadata': {}}
    first = repo.import_items([item])
    assert first == {'new_count': 1, 'changed_count': 0}
    assert repo.import_items([item]) == {'new_count': 0, 'changed_count': 0}
    task = repo.snapshot()['tasks'][0]
    repo.update_task(task['id'], {'status': 'done'})
    item['body'] = 'Q1 revised'
    assert repo.import_items([item]) == {'new_count': 0, 'changed_count': 1}
    reopened = Repository(tmp_path / 'test.db')
    assert reopened.snapshot()['tasks'][0]['status'] == 'done'
    assert reopened.snapshot()['sources'][0]['revision'] == 2


def test_delete_one_source_preserves_other_and_invalidates_derived_drafts(tmp_path):
    repo = Repository(tmp_path / 'test.db')
    repo.import_items([{'provider_id': x, 'kind': 'project_note', 'title': x, 'body': x} for x in ['one', 'two']])
    one = next(x for x in repo.snapshot()['sources'] if x['title'] == 'one')
    repo.save_draft({'id': 'd1', 'kind': 'meeting_brief', 'title': 'Brief', 'markdown': 'one', 'source_refs': [{'id': one['id'], 'revision': 1}], 'provider': 'demo', 'model': 'template', 'status': 'review_needed'})
    repo.delete_source(one['id'])
    assert [x['title'] for x in repo.snapshot()['sources']] == ['two']
    assert repo.snapshot()['drafts'] == []


def test_profile_and_notes_survive_restart(tmp_path):
    repo = Repository(tmp_path / 'test.db')
    repo.update_profile({'name': 'Kevin', 'goal': 'Understand the method'})
    repo.import_items([{'title': 'Project A', 'kind': 'project_note', 'body': 'Next: test the camera'}])
    state = Repository(tmp_path / 'test.db').snapshot()
    assert state['profile']['goal'] == 'Understand the method'
    assert state['sources'][0]['body'] == 'Next: test the camera'
