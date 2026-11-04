"""Event-built bounded observe/compare/plan/prepare/verify/remember agent."""
import hashlib
import json
from uuid import uuid4
from app.model import ModelError, MODEL
from app.repository import now_iso


def context(sources, tasks):
    ids = {s['id'] for s in sources}
    return {'sources': sorted([{k:v for k,v in s.items() if k!='_vision_images'} for s in sources], key=lambda s: s['id']),
            'tasks': sorted([{k: t.get(k) for k in ('id','source_id','status','due_at','snoozed_until')} for t in tasks if t['source_id'] in ids], key=lambda t: t['id'])}


def fingerprint(value):
    stable = {'sources': [(s['id'], s['revision'], s['content_hash']) for s in value['sources']], 'tasks': value['tasks']}
    return hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()


def changes(previous, current):
    old = {s['id']: s for s in previous.get('sources', [])}
    result = []
    for s in current['sources']:
        before = old.get(s['id'])
        if not before or before['content_hash'] != s['content_hash']:
            result.append({'kind': 'changed' if before else 'new', 'source_id': s['id'], 'before': before, 'after': s})
    old_tasks = {t['id']: t for t in previous.get('tasks', [])}
    for t in current['tasks']:
        if t['id'] in old_tasks and old_tasks[t['id']] != t:
            result.append({'kind': 'progress', 'source_id': t['source_id'], 'before': old_tasks[t['id']], 'after': t})
    return result


def model_changes(delta):
    # Historical bodies/metadata are never transmitted under current-source consent.
    return [{**c, 'before': {k: v for k, v in (c['before'] or {}).items() if k in {'due_at','status','revision','content_hash'}},
             'after': {k: v for k, v in c['after'].items() if k in {'title','due_at','status','revision','content_hash'}}} for c in delta]


class AgentRunner:
    def __init__(self, repo, client):
        self.repo, self.client = repo, client

    def run(self, sources):
        if not 1 <= len(sources) <= 4 or any(s['metadata'].get('active_assessment') or s['metadata'].get('assistance_restricted') for s in sources):
            raise ValueError('Choose one to four unrestricted sources.')
        snapshot = self.repo.snapshot()
        supplied = context(sources, snapshot['tasks'])
        scope_text=','.join(sorted(s['id'] for s in sources))
        if any(s.get('_vision_images') for s in sources):
            scope_text+=json.dumps(sorted((s['id'],[i['page'] for i in s.get('_vision_images',[])]) for s in sources))
        scope = hashlib.sha256(scope_text.encode()).hexdigest()
        previous = next((p for p in self.repo.records('agent_checkpoints') if p['id'] == scope), {})
        digest = fingerprint(supplied)
        if previous.get('fingerprint') == digest:
            return {'status': 'unchanged', 'message': 'No source or progress changes. No Meta calls made.', 'call_count': 0}
        delta = changes(previous.get('context', {}), supplied)
        run = {'id': uuid4().hex, 'scope': scope, 'started_at': now_iso(), 'status': 'running',
               'fingerprint': digest, 'source_refs': [{'id': s['id'], 'revision': s['revision'], 'content_hash': s['content_hash']} for s in sources],
               'changes': model_changes(delta), 'call_count': 0, 'draft_ids': [], 'model': MODEL}
        try:
            run['call_count'] += 1
            plan = self.client.plan(sources, supplied['tasks'], model_changes(delta))
            run['plan'] = plan
            drafts = []
            by_id = {s['id']: s for s in sources}
            # Defense in depth even with an alternate/injected provider client.
            actions = plan['actions']
            blocked = {t['source_id'] for t in supplied['tasks'] if t['status'] != 'open'}
            if len(actions) > 2 or len({a['source_id'] for a in actions}) != len(actions) or any(a['source_id'] not in by_id or a['source_id'] in blocked for a in actions):
                raise ModelError('Invalid or completed action target. No outputs saved.')
            for action in actions:
                source = by_id[action['source_id']]
                support = [s for s in sources if s['id'] != source['id']]
                run['call_count'] += 1
                draft = self.client.generate([source] + support[:3])
                drafts.append({**draft, 'id': 'agent-' + uuid4().hex, 'title': source['title'] + ' · Sidekick', 'agent_run_id': run['id']})
            run.update(status='completed', finished_at=now_iso(), draft_ids=[d['id'] for d in drafts],
                       verification='Source references and input state checked. Content needs your review.')
            with self.repo.db() as db:
                db.execute('BEGIN IMMEDIATE')
                current_sources = {s['id']: s for s in self.repo.records('sources', db)}
                if any(s['id'] not in current_sources for s in sources):
                    raise ValueError('Source material changed during the agent run. No outputs saved.')
                latest = context([current_sources[s['id']] for s in sources], self.repo.records('tasks', db))
                if fingerprint(latest) != digest:
                    raise ValueError('Source material or task progress changed during the agent run. No outputs saved.')
                for draft in drafts:
                    self.repo._put(db, 'drafts', draft)
                self.repo._put(db, 'agent_runs', run)
                self.repo._put(db, 'agent_checkpoints', {'id': scope, 'fingerprint': digest, 'context': supplied})
            return run
        except (ModelError, ValueError):
            run.update(status='failed', finished_at=now_iso(), draft_ids=[], error='Preparation failed; no new outputs saved. Check usage before retrying.')
            with self.repo.db() as db:
                self.repo._put(db, 'agent_runs', run)
            raise
