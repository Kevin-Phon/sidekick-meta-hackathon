from datetime import datetime, timezone
from app.scheduler import next_daily_run, should_catch_up


def test_pacific_time_crosses_daylight_saving_boundary():
    assert next_daily_run(datetime(2026, 10, 31, 17, tzinfo=timezone.utc)).isoformat() == '2026-11-01T17:00:00+00:00'
    assert next_daily_run(datetime(2026, 10, 31, 15, tzinfo=timezone.utc)).isoformat() == '2026-10-31T16:00:00+00:00'


def test_startup_catch_up_only_once_per_local_day():
    now = datetime(2026, 10, 20, 18, tzinfo=timezone.utc)
    assert should_catch_up(now, None) is True
    assert should_catch_up(now, '2026-10-20T17:00:00+00:00') is False
    assert should_catch_up(datetime(2026, 10, 20, 14, tzinfo=timezone.utc), None) is False
