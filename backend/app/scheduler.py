from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ZONE = ZoneInfo('America/Los_Angeles')


def next_daily_run(now):
    local = now.astimezone(ZONE)
    target = local.replace(hour=9, minute=0, second=0, microsecond=0)
    if local >= target:
        target += timedelta(days=1)
    return target.astimezone(timezone.utc)


def should_catch_up(now, last_run):
    local = now.astimezone(ZONE)
    if local.hour < 9:
        return False
    if not last_run:
        return True
    return datetime.fromisoformat(last_run).astimezone(ZONE).date() < local.date()
