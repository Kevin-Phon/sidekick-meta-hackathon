import json
import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
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
            db.execute('CREATE TABLE IF NOT EXISTS documents (source_id TEXT PRIMARY KEY, source_hash TEXT NOT NULL, page_count INTEGER NOT NULL, content BLOB NOT NULL)')
            db.execute('PRAGMA user_version = 2')
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

    def import_items(self, items, document=None, expected_workspace=None):
        active = self.update_profile({}).get('active_workspace')
        if expected_workspace is not None and (active or 'legacy')!=expected_workspace:
            raise ValueError('Your workspace changed. Import again in the intended workspace.')
        if active and active != 'legacy' and isinstance(items, list):
            items = [{**item, 'connection_id': f'workspace:{active}:' + str(item.get('connection_id', 'imports')),
                      'metadata': {**(item.get('metadata') or {}), 'workspace_id': active}}
                     if isinstance(item, dict) and isinstance(item.get('metadata') or {}, dict) else item for item in items]
        normalized = normalize_items(items)
        counts = {'new_count': 0, 'changed_count': 0}
        with self.db() as db:
            if expected_workspace is not None:
                db.execute('BEGIN IMMEDIATE')
                row=db.execute("SELECT data FROM settings WHERE id='profile'").fetchone()
                current=(json.loads(row[0]).get('active_workspace') if row else None) or 'legacy'
                if current!=expected_workspace:raise ValueError('Your workspace changed. No mail was saved.')
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
                if document is not None:
                    db.execute('INSERT INTO documents VALUES(?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET source_hash=excluded.source_hash,page_count=excluded.page_count,content=excluded.content', (item['id'],item['content_hash'],document['page_count'],document['content']))
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
            row = db.execute('SELECT data FROM settings WHERE id=?', ('profile',)).fetchone()
            profile = json.loads(row[0]) if row else {}
            self._put(db, 'checks', {**check, 'workspace_id': profile.get('active_workspace') or 'legacy'})

    def update_profile(self, patch):
        with self.db() as db:
            row = db.execute('SELECT data FROM settings WHERE id=?', ('profile',)).fetchone()
            profile = json.loads(row[0]) if row else {'name': '', 'goal': '', 'daily_enabled': False, 'timezone': 'America/Los_Angeles'}
            if 'active_workspace' in patch:
                allowed = {'legacy'} | {w['id'] for w in self.records('workspaces', db)}
                if not isinstance(patch['active_workspace'], str) or patch['active_workspace'] not in allowed:
                    raise ValueError('Choose an existing workspace.')
            for key in {'name', 'goal', 'daily_enabled', 'active_workspace'}:

                if key in patch:
                    profile[key] = patch[key]
            db.execute('INSERT INTO settings VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data', ('profile', json.dumps(profile)))
        return profile

    def snapshot(self):
        with self.db() as db:
            row = db.execute('SELECT data FROM settings WHERE id=?', ('profile',)).fetchone()
            profile = json.loads(row[0]) if row else {'name': '', 'goal': '', 'daily_enabled': False, 'timezone': 'America/Los_Angeles'}
            data = {kind: self.records(kind, db) for kind in ('sources', 'tasks', 'drafts', 'checks')}
            active = profile.get('active_workspace')
            if active:
                data['sources'] = [s for s in data['sources'] if (s['metadata'].get('workspace_id') or 'legacy') == active]
                ids = {s['id'] for s in data['sources']}
                data['tasks'] = [t for t in data['tasks'] if t['source_id'] in ids]
                data['drafts'] = [d for d in data['drafts'] if d['source_refs'] and all(r['id'] in ids for r in d['source_refs'])]
                data['checks'] = [c for c in data['checks'] if (c.get('workspace_id') or 'legacy') == active]
            for source in data['sources']:
                row=db.execute('SELECT page_count FROM documents WHERE source_id=? AND source_hash=?',(source['id'],source['content_hash'])).fetchone()
                source['visual_document']={'page_count':row[0]} if row else None
            return {**data, 'profile': profile, 'workspaces': [{'id':'legacy','name':'Previous workspace'}] + self.records('workspaces', db)}

    def create_workspace(self, name='My workspace'):
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
            raise ValueError('Name the workspace in 1–100 characters.')
        workspace = {'id': uuid4().hex, 'name': name.strip(), 'created_at': now_iso()}
        with self.db() as db:
            self._put(db, 'workspaces', workspace)
        self.update_profile({'active_workspace': workspace['id'], 'daily_enabled': False})
        return workspace

    def attach_document(self, source_id, expected_hash, content, page_count):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            old=next((s for s in self.records('sources',db) if s['id']==source_id),None)
            if not old or old['content_hash']!=expected_hash:
                raise ValueError('Source changed before original PDF recovery.')
            item=normalize_items([{**old,'metadata':{**old['metadata'],'pdf_sha256':hashlib.sha256(content).hexdigest()}}])[0]
            item['revision']=old['revision']+1
            self._put(db,'sources',item)
            for draft in self.records('drafts',db):
                if any(r['id']==source_id for r in draft['source_refs']):
                    db.execute('DELETE FROM records WHERE kind=? AND id=?',('drafts',draft['id']))
            db.execute('INSERT INTO documents VALUES(?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET source_hash=excluded.source_hash,page_count=excluded.page_count,content=excluded.content',(source_id,item['content_hash'],page_count,content))

    def document(self, source):
        with self.db() as db:
            row=db.execute('SELECT page_count,content FROM documents WHERE source_id=? AND source_hash=?',(source['id'],source['content_hash'])).fetchone()
            return {'page_count':row[0],'content':row[1]} if row else None

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
            db.execute('DELETE FROM documents WHERE source_id=?',(source_id,))
            deleted = db.execute('DELETE FROM records WHERE kind=? AND id=?', ('sources', source_id)).rowcount
            if not deleted:
                raise KeyError(source_id)
