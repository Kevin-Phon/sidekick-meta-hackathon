import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from app.sources.imports import normalize_items


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class Repository:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS records (kind TEXT, id TEXT, data TEXT NOT NULL, PRIMARY KEY(kind,id))')
            db.execute('CREATE TABLE IF NOT EXISTS settings (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
            db.execute('PRAGMA user_version = 1')
        self.path.chmod(0o600)

    @contextmanager
    def db(self):
        connection = sqlite3.connect(self.path, timeout=15)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def records(self, kind, db=None):
        if db is None:
            with self.db() as conn:
                return self.records(kind, conn)
        return [json.loads(row[0]) for row in db.execute('SELECT data FROM records WHERE kind=? ORDER BY rowid', (kind,))]

    def _put(self, db, kind, value):
        db.execute('INSERT INTO records(kind,id,data) VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data',
                   (kind, value['id'], json.dumps(value)))

    def import_items(self, items):
        normalized = normalize_items(items)
        counts = {'new_count': 0, 'changed_count': 0}
        with self.db() as db:
            existing = {x['id']: x for x in self.records('sources', db)}
            tasks = {x['source_id']: x for x in self.records('tasks', db)}
            for item in normalized:
                old = existing.get(item['id'])
                changed = old and old['content_hash'] != item['content_hash']
                item['revision'] = old['revision'] + int(bool(changed)) if old else 1
                if not old:
                    counts['new_count'] += 1
                elif changed:
                    counts['changed_count'] += 1
                if changed:
                    for draft in self.records('drafts', db):
                        if any(r['id'] == item['id'] for r in draft['source_refs']):
                            db.execute('DELETE FROM records WHERE kind=? AND id=?', ('drafts', draft['id']))
                self._put(db, 'sources', item)
                existing[item['id']] = item
                if item['kind'] in {'assignment', 'project_note'}:
                    previous = tasks.get(item['id'], {})
                    task = dict(id='task-' + item['id'], source_id=item['id'], title=item['title'],
                                status=previous.get('status', 'open'), due_at=item['due_at'],
                                snoozed_until=previous.get('snoozed_until'),
                                priority_override=previous.get('priority_override'),
                                reason='Assignment deadline' if item['kind'] == 'assignment' else 'Continue your project')
                    self._put(db, 'tasks', task)
        return counts

    def update_task(self, task_id, patch):
        with self.db() as db:
            task = next((x for x in self.records('tasks', db) if x['id'] == task_id), None)
            if task is None:
                raise KeyError(task_id)
            if patch.get('status', task['status']) not in {'open', 'done', 'snoozed'}:
                raise ValueError('Unknown task state')
            task.update({key: value for key, value in patch.items() if key in {'status', 'snoozed_until', 'priority_override'}})
            self._put(db, 'tasks', task)
        return task

    def save_draft(self, draft):
        with self.db() as db:
            self._put(db, 'drafts', {**draft, 'generated_at': draft.get('generated_at', now_iso())})

    def save_generated_draft(self, draft, supplied_sources):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            current = {(s['id'], s['revision'], s['content_hash']) for s in self.records('sources', db)}
            if any((s['id'], s['revision'], s['content_hash']) not in current for s in supplied_sources):
                raise ValueError('Source material changed during generation. The draft was not saved; reload before retrying.')
            self._put(db, 'drafts', {**draft, 'generated_at': draft.get('generated_at', now_iso())})

    def save_check(self, check):
        with self.db() as db:
            self._put(db, 'checks', check)

    def update_profile(self, patch):
        with self.db() as db:
            row = db.execute('SELECT data FROM settings WHERE id=?', ('profile',)).fetchone()
            profile = json.loads(row[0]) if row else {'name': 'Kevin', 'goal': 'Learn, stay organized, and keep moving.', 'daily_enabled': False, 'timezone': 'America/Los_Angeles'}
            for key in {'name', 'goal', 'daily_enabled'}:
                if key in patch:
                    profile[key] = patch[key]
            db.execute('INSERT INTO settings VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data', ('profile', json.dumps(profile)))
        return profile

    def snapshot(self):
        with self.db() as db:
            row = db.execute('SELECT data FROM settings WHERE id=?', ('profile',)).fetchone()
            profile = json.loads(row[0]) if row else {'name': 'Kevin', 'goal': 'Learn, stay organized, and keep moving.', 'daily_enabled': False, 'timezone': 'America/Los_Angeles'}
            return {**{kind: self.records(kind, db) for kind in ('sources', 'tasks', 'drafts', 'checks')}, 'profile': profile}

    def delete_source(self, source_id):
        with self.db() as db:
            # Withdraw the selected source from derived agent memory as well.
            affected_drafts = set()
            for run in self.records('agent_runs', db):
                if any(ref['id'] == source_id for ref in run.get('source_refs', [])):
                    affected_drafts.update(run.get('draft_ids', []))
                    db.execute('DELETE FROM records WHERE kind=? AND id=?', ('agent_runs', run['id']))
            for checkpoint in self.records('agent_checkpoints', db):
                if any(s['id'] == source_id for s in checkpoint.get('context', {}).get('sources', [])):
                    db.execute('DELETE FROM records WHERE kind=? AND id=?', ('agent_checkpoints', checkpoint['id']))
            for draft_id in affected_drafts:
                db.execute('DELETE FROM records WHERE kind=? AND id=?', ('drafts', draft_id))
            for draft in self.records('drafts', db):
                if any(ref['id'] == source_id for ref in draft['source_refs']):
                    db.execute('DELETE FROM records WHERE kind=? AND id=?', ('drafts', draft['id']))
            db.execute('DELETE FROM records WHERE kind=? AND id=?', ('tasks', 'task-' + source_id))
            deleted = db.execute('DELETE FROM records WHERE kind=? AND id=?', ('sources', source_id)).rowcount
            if not deleted:
                raise KeyError(source_id)
