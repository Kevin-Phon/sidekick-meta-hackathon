import pytest
from app.sources.imports import normalize_items


def test_unknown_timezone_is_not_invented():
    item = normalize_items([{'title': 'HW', 'kind': 'assignment', 'body': 'Question', 'due_at': '2026-11-02T12:00:00'}])[0]
    assert item['due_at'] is None
    assert item['due_original'] == '2026-11-02T12:00:00'
    assert item['timezone_known'] is False


def test_explicit_deadline_keeps_absolute_time_and_links_are_safe():
    item = normalize_items([{'title': 'HW', 'kind': 'assignment', 'body': '<script>alert(1)</script>', 'due_at': '2026-11-02T12:00:00-08:00', 'url': 'javascript:alert(1)'}])[0]
    assert item['due_at'] == '2026-11-02T20:00:00+00:00'
    assert item['url'] is None
    assert item['body'] == '<script>alert(1)</script>'


def test_invalid_source_is_rejected():
    with pytest.raises(ValueError):
        normalize_items([{'title': '', 'kind': 'assignment', 'body': 'Q'}])
