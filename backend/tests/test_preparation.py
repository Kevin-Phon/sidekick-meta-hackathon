import pytest
from app.repository import Repository
from app.preparation import prepare, validate_refs
from app.demo import demo_items


def test_demo_prepares_separate_homework_guide_and_meeting_without_marking_done(tmp_path):
    repo = Repository(tmp_path / 'test.db')
    repo.import_items(demo_items())
    result = prepare(repo)
    assert result['draft_count'] >= 3
    state = repo.snapshot()
    assert {'homework', 'study_guide', 'meeting_brief'} <= {d['kind'] for d in state['drafts']}
    hw = next(d for d in state['drafts'] if d['kind'] == 'homework')
    assert 'A ∩ B = {3, 4}' in hw['markdown']
    assert hw['provider'] == 'demo_template'
    assert hw['status'] == 'review_needed'
    assert all(t['status'] == 'open' for t in state['tasks'])
    assert prepare(repo)['draft_count'] == 0
    assert len(repo.snapshot()['drafts']) == len(state['drafts'])


def test_real_import_does_not_receive_fabricated_answer(tmp_path):
    repo = Repository(tmp_path / 'test.db')
    repo.import_items([{'title': 'Real homework', 'kind': 'assignment', 'body': 'Use the missing data file to find the result.', 'metadata': {'missing_sources': ['data.csv']}}])
    prepare(repo)
    draft = repo.snapshot()['drafts'][0]
    assert draft['status'] == 'needs_input'
    assert 'data.csv' in draft['markdown']
    assert 'not connected' in draft['markdown']


def test_active_assessment_only_gets_preparation(tmp_path):
    repo = Repository(tmp_path / 'test.db')
    repo.import_items([{'title': 'Exam', 'kind': 'assignment', 'body': 'Solve this', 'metadata': {'active_assessment': True}}])
    prepare(repo)
    draft = repo.snapshot()['drafts'][0]
    assert draft['status'] == 'restricted'
    assert draft['kind'] == 'study_guide'


def test_invalid_reference_rejected():
    with pytest.raises(ValueError):
        validate_refs([{'id': 'invented', 'revision': 1}], [{'id': 'real', 'revision': 1}])


def test_changed_sample_lecture_does_not_reuse_prewritten_guide(tmp_path):
    repo = Repository(tmp_path / 'test.db')
    items = demo_items()
    next(s for s in items if s['provider_id'] == 'sample-lecture')['body'] = 'New lecture on graphs.'
    repo.import_items(items)
    prepare(repo)
    state = repo.snapshot()
    lecture = next(s for s in state['sources'] if s['provider_id'] == 'sample-lecture')
    guide = next(d for d in state['drafts'] if d['source_refs'][0]['id'] == lecture['id'])
    assert guide['provider'] == 'source_outline'
    assert 'New lecture on graphs.' in guide['markdown']
    hw = next(d for d in state['drafts'] if d['kind'] == 'homework')
    assert lecture['id'] not in [r['id'] for r in hw['source_refs']]
