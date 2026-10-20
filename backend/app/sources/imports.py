import hashlib
import json
from datetime import datetime, timezone
from urllib.parse import urlparse

KINDS = {'assignment', 'lecture', 'announcement', 'project_note', 'mail'}


def normalize_items(items):
    if not isinstance(items, list) or len(items) > 200:
        raise ValueError('Import a list containing at most 200 items.')
    output = []
    for raw in items:
        title = str(raw.get('title', '')).strip()
        body = str(raw.get('body', '')).strip()
        kind = raw.get('kind', 'lecture')
        if not title or kind not in KINDS or len(body) > 500_000:
            raise ValueError('Each item needs a title, a supported type, and text under 500,000 characters.')
        original = raw.get('due_original') or raw.get('due_at') or None
        due = None
        if original:
            try:
                parsed = datetime.fromisoformat(original.replace('Z', '+00:00'))
                if parsed.tzinfo:
                    due = parsed.astimezone(timezone.utc).isoformat()
            except (ValueError, AttributeError):
                pass
        url = str(raw.get('url') or '')
        if urlparse(url).scheme != 'https' or not urlparse(url).hostname:
            url = None
        metadata = raw.get('metadata') or {}
        if not isinstance(metadata, dict):
            raise ValueError('Source metadata must be an object.')
        connection = str(raw.get('connection_id', 'imports'))[:100]
        provider = str(raw.get('provider_id') or hashlib.sha256(f'{kind}:{title}'.encode()).hexdigest()[:24])
        item = dict(provider_id=provider[:200], connection_id=connection, kind=kind,
                    title=title[:300], body=body, url=url, due_at=due,
                    due_original=original, timezone_known=bool(due), metadata=metadata)
        item['id'] = hashlib.sha256(f'{connection}:{provider}'.encode()).hexdigest()[:24]
        item['content_hash'] = hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest()
        item['fetched_at'] = datetime.now(timezone.utc).isoformat()
        item['source_updated_at'] = raw.get('source_updated_at')
        output.append(item)
    return output
