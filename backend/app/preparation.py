import hashlib
from uuid import uuid4
from app.demo import HOMEWORK, GUIDE, demo_items
from app.repository import now_iso


def validate_refs(refs, sources):
    allowed = {(s['id'], s['revision']) for s in sources}
    if not refs or any((r['id'], r['revision']) not in allowed for r in refs):
        raise ValueError('Draft references unavailable source revisions.')


def prepare(repo):
    state = repo.snapshot()
    drafts = {d['id'] for d in state['drafts']}
    created = []
    sample_bodies = {s['provider_id']: s['body'] for s in demo_items()}
    def unchanged_sample(source):
        return source['connection_id'] == 'demo' and source['body'] == sample_bodies.get(source['provider_id'])
    for source in state['sources']:
        kind = source['kind']
        if kind not in {'assignment', 'lecture', 'project_note', 'mail'}:
            continue
        meta = source['metadata']
        refs = [{'id': source['id'], 'revision': source['revision']}]
        status, provider = 'review_needed', 'source_outline'
        if meta.get('active_assessment') or meta.get('assistance_restricted'):
            draft_kind, status = 'study_guide', 'restricted'
            content = '## Study preparation\nThis item is marked as an active assessment or has assistance restrictions. Review your permitted notes and practice related concepts separately. No worked assessment answer was prepared.'
        elif unchanged_sample(source) and meta.get('sample_artifact') == 'sets-homework':
            draft_kind, content, provider = 'homework', HOMEWORK, 'demo_template'
            lecture = next((s for s in state['sources'] if s['connection_id'] == 'demo' and s['provider_id'] == 'sample-lecture' and unchanged_sample(s)), None)
            if lecture:
                refs.append({'id': lecture['id'], 'revision': lecture['revision']})
        elif unchanged_sample(source) and meta.get('sample_artifact') == 'sets-guide':
            draft_kind, content, provider = 'study_guide', GUIDE, 'demo_template'
        elif kind == 'assignment':
            draft_kind, status = 'homework', 'needs_input'
            missing = ', '.join(meta.get('missing_sources', [])) or 'A verified AI connection and any required lecture/rubric files'
            content = f'## Assignment\n{source["body"]}\n\n## What is still needed\n{missing}.\n\nMeta AI is not connected. No candidate answer has been generated.\n\n## Worked-draft structure\nOnce the sources and model are available, prepare: question meaning, required concepts, method, worked steps, candidate answer, and a result check.'
        elif kind == 'lecture':
            draft_kind = 'study_guide'
            content = f'## Source notes\n{source["body"]}\n\n## Study sequence\n1. Identify the key ideas in the source above.\n2. Explain each one in your own words.\n3. Write a practice example and check it against the source.\n\nThis is a source-based outline. Meta AI is not connected; no additional explanations have been generated.'
        elif kind == 'mail':
            draft_kind, status = 'mail_reply', 'needs_input'
            content = f'## Saved message\n{source["body"]}\n\n## Reply preparation\nRun Sidekick with this selected message to prepare a source-grounded reply draft. Nothing has been sent. This is a local source outline; no AI reply has been generated.'
        else:
            draft_kind = 'meeting_brief'
            content = f'## Your recorded progress\n{source["body"]}\n\n## A short meeting structure\n- What I finished\n- What is in progress\n- What is blocked\n- My next step and any help I need\n\nUse the recorded progress above. Add missing facts yourself. This is a source-based outline, not a live AI generation.'
        fingerprint = ':'.join(f'{r["id"]}@{r["revision"]}' for r in refs)
        draft_id = hashlib.sha256(f'{draft_kind}:{fingerprint}'.encode()).hexdigest()[:24]
        if draft_id in drafts:
            continue
        validate_refs(refs, state['sources'])
        repo.save_draft(dict(id=draft_id, kind=draft_kind, title=source['title'], markdown=content,
                             status=status, source_refs=refs, provider=provider, model='none', generated_at=now_iso()))
        drafts.add(draft_id)
        created.append(draft_id)
    stamp = now_iso()
    repo.save_check(dict(id=uuid4().hex, started_at=stamp, finished_at=stamp, draft_ids=created,
                         draft_count=len(created), status='prepared', mode='local',
                         message='Reviewed saved/imported material only. No external accounts were checked.'))
    return {'draft_count': len(created), 'draft_ids': created, 'checked_at': stamp}
