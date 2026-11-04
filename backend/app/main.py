import asyncio
import hashlib
import json
import os
from uuid import uuid4
import secrets
import threading
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pypdf import PdfReader

from app.config import Settings
from app.demo import demo_items
from app.preparation import prepare
from app.model import MetaClient, ModelError, MODEL
from app.repository import Repository
from app.agent import AgentRunner, context, fingerprint
from app.agent_demo import agent_demo
from app.scheduler import next_daily_run, should_catch_up

ROOT = Path(__file__).resolve().parents[2]
LIMIT = 10 * 1024 * 1024


async def read_limited(request):
    chunks, length = [], 0
    async for chunk in request.stream():
        length += len(chunk)
        if length > LIMIT:
            raise HTTPException(413, 'Keep imports under 10 MB.')
        chunks.append(chunk)
    return b''.join(chunks)


def create_app(settings):
    repo = Repository(settings.data_dir / 'sidekick.db')
    session = secrets.token_urlsafe(32)
    run_lock = threading.Lock()
    model_state = {'key': os.environ.get('MODEL_API_KEY', ''), 'verified': False, 'last_error': ''}

    def model_status():
        return {'configured': bool(model_state['key']), 'verified': model_state['verified'],
                'model': MODEL, 'mode': 'Standard', 'last_error': model_state['last_error']}

    def check():
        if not run_lock.acquire(blocking=False):
            raise HTTPException(409, 'A preparation is already running.')
        try:
            return prepare(repo)
        finally:
            run_lock.release()

    async def scheduled_loop():
        while True:
            state = repo.snapshot()
            last = state['checks'][-1]['finished_at'] if state['checks'] else None
            if state['profile']['daily_enabled'] and should_catch_up(datetime.now(timezone.utc), last):
                try:
                    await asyncio.to_thread(check)
                except Exception:
                    # Retry next tick; do not claim a successful preparation.
                    pass
            await asyncio.sleep(30)

    @asynccontextmanager
    async def lifespan(app):
        worker = asyncio.create_task(scheduled_loop()) if settings.run_scheduler else None
        yield
        if worker:
            worker.cancel()
            with suppress(asyncio.CancelledError):
                await worker

    app = FastAPI(title='Sidekick local companion', lifespan=lifespan, docs_url=None, redoc_url=None)

    @app.middleware('http')
    async def protect(request, call_next):
        host = request.url.hostname
        if host not in {'127.0.0.1', 'localhost', 'testserver', '[::1]', '::1'}:
            return JSONResponse({'detail': 'Only local access is allowed.'}, status_code=400)
        if request.url.path.startswith('/api/') and request.url.path != '/api/bootstrap':
            if not secrets.compare_digest(request.cookies.get('sidekick_session', ''), session):
                return JSONResponse({'detail': 'Reload Sidekick to establish your local session.'}, status_code=403)
            if request.method not in {'GET', 'HEAD'}:
                origin = request.headers.get('origin', '')
                valid_origins = {f'http://{request.headers.get("host")}', 'http://127.0.0.1:5173', 'http://localhost:5173'}
                if origin not in valid_origins or not secrets.compare_digest(request.headers.get('x-sidekick-token', ''), session):
                    return JSONResponse({'detail': 'Local session approval is missing.'}, status_code=403)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'none'; object-src 'none'; frame-src 'none'; base-uri 'self'; form-action 'self'; style-src 'self' 'unsafe-inline'"
        return response

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({'detail': str(exc)}, status_code=400)

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse({'detail': 'That saved item was not found.'}, status_code=404)

    @app.get('/api/bootstrap')
    def bootstrap():
        response = JSONResponse({'token': session})
        response.set_cookie('sidekick_session', session, httponly=True, samesite='strict')
        return response

    @app.get('/api/state')
    def state():
        saved = repo.snapshot()
        visible_ids = {s['id'] for s in saved['sources']}
        runs = [r for r in repo.records('agent_runs') if all(ref['id'] in visible_ids for ref in r['source_refs'])][-12:]
        checkpoints = {p['id']: p for p in repo.records('agent_checkpoints')}
        by_id = {s['id']: s for s in saved['sources']}
        for run in runs:
            ids = [r['id'] for r in run['source_refs']]
            run['stale'] = any(i not in by_id for i in ids) or fingerprint(context([by_id[i] for i in ids if i in by_id], saved['tasks'])) != run['fingerprint']
        return {**saved, 'agent_runs': runs, 'model': model_status(), 'connections': [
            {'id': 'imports', 'name': 'Course & project files', 'status': 'local', 'detail': 'Saved snapshots. Import new material to update them.'},
            {'id': 'canvas', 'name': 'Canvas', 'status': 'blocked', 'detail': 'CPP requires an administrator-approved connection. Import course files for now.'},
            {'id': 'gmail', 'name': 'Gmail', 'status': 'not_connected', 'detail': 'Independent app authorization is not configured.'},
            {'id': 'meta', 'name': 'Meta AI', 'status': 'connected' if model_state['verified'] else 'configured' if model_state['key'] else 'not_connected', 'detail': 'Muse Spark 1.3 Standard. Selected-source requests only. ' + ('A real generation has succeeded.' if model_state['verified'] else 'Live generation not yet verified.')}],
            'next_run': next_daily_run(datetime.now(timezone.utc)).isoformat(),
            'mode': 'sample' if any(x['metadata'].get('demo') for x in saved['sources']) else 'local',
            'eligibility': 'Agent workflow built November 3 on an October 20–21 preparatory prototype. See the event-work disclosure; organizer eligibility is unconfirmed.'}

    @app.post('/api/demo')
    def load_demo():
        counts = repo.import_items(demo_items())
        return {**counts, **check()}

    @app.post('/api/import')
    async def import_json(request: Request):
        try:
            payload = json.loads(await read_limited(request))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ValueError('That file is not valid JSON.')
        items = payload.get('items') if isinstance(payload, dict) else payload
        counts = repo.import_items(items)
        return {**counts, **check()}

    @app.post('/api/import/file')
    async def import_file(request: Request, filename: str, kind: str = 'lecture', title: str = '', course: str = '', due_at: str = '', project: str = ''):
        suffix = Path(filename).suffix.lower()
        if suffix not in {'.pdf', '.txt', '.md', '.json'} or '/' in filename or '\\' in filename:
            raise ValueError('Choose a PDF, text, Markdown, or JSON file.')
        content = await read_limited(request)
        if suffix == '.json':
            try:
                payload = json.loads(content)
                items = payload.get('items') if isinstance(payload, dict) else payload
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise ValueError('That JSON file could not be read.')
        else:
            try:
                if suffix == '.pdf':
                    pdf = PdfReader(BytesIO(content))
                    if len(pdf.pages) > 100:
                        raise ValueError('Import a PDF with no more than 100 pages.')
                    text = '\n\n'.join(page.extract_text() or '' for page in pdf.pages)
                else:
                    text = content.decode('utf-8-sig')
            except Exception:
                raise ValueError('Could not extract text. Use a text-based PDF or import a text/Markdown version.')
            if not text.strip():
                raise ValueError('No readable text was found. Scanned files need text extraction first.')
            identity = hashlib.sha256(json.dumps([filename, kind, course, title, text], ensure_ascii=False).encode()).hexdigest()
            items = [{'provider_id': identity, 'title': title or Path(filename).stem, 'kind': kind,
                      'body': text, 'due_at': due_at or None, 'metadata': {'course': course, 'project': project, 'filename': filename}}]
        counts = repo.import_items(items)
        return {**counts, **check()}

    @app.post('/api/checks')
    def prepare_saved():
        return check()

    @app.patch('/api/tasks/{task_id}')
    async def task(task_id: str, request: Request):
        patch = json.loads(await read_limited(request))
        if not isinstance(patch, dict):
            raise ValueError('Task updates must be an object.')
        return repo.update_task(task_id, patch)

    @app.post('/api/workspaces')
    async def new_workspace(request: Request):
        payload = json.loads(await read_limited(request))
        if not isinstance(payload, dict):
            raise ValueError('Workspace details must be an object.')
        if not run_lock.acquire(blocking=False):
            raise HTTPException(409, 'Wait for the current preparation before changing workspace.')
        try:
            return repo.create_workspace(payload.get('name', 'My workspace'))
        finally:
            run_lock.release()

    @app.patch('/api/profile')
    async def profile(request: Request):
        patch = json.loads(await read_limited(request))
        if not isinstance(patch, dict) or any(not isinstance(patch[x], str) or len(patch[x]) > 3000 for x in ('name', 'goal') if x in patch):
            raise ValueError('Name and goals must be text under 3,000 characters.')
        if 'daily_enabled' in patch and not isinstance(patch['daily_enabled'], bool):
            raise ValueError('Daily preparation must be on or off.')
        if 'active_workspace' in patch:
            if not run_lock.acquire(blocking=False):
                raise HTTPException(409, 'Wait for the current preparation before changing workspace.')
            try:
                return repo.update_profile(patch)
            finally:
                run_lock.release()
        return repo.update_profile(patch)

    @app.delete('/api/sources/{source_id}')
    def delete(source_id: str):
        repo.delete_source(source_id)
        return {'deleted_id': source_id}

    @app.get('/api/drafts/{draft_id}/download')
    def download(draft_id: str):
        draft = next((d for d in repo.snapshot()['drafts'] if d['id'] == draft_id), None)
        if not draft:
            raise KeyError(draft_id)
        refs = '\n'.join(f'- {r["id"]}, revision {r["revision"]}' for r in draft['source_refs'])
        exported = f'# {draft["title"]}\n\nReview required. Provider: {draft["provider"]}; model: {draft["model"]}.\nGenerated: {draft["generated_at"]}\n\n{draft["markdown"]}\n\n## Source references\n{refs}\n'
        return Response(exported, media_type='text/markdown', headers={'Content-Disposition': f'attachment; filename="sidekick-{draft["kind"]}.md"'})

    @app.post('/api/model/key')
    async def model_key(request: Request):
        payload = json.loads(await read_limited(request))
        key = payload.get('key') if isinstance(payload, dict) else None
        if not isinstance(key, str) or len(key) > 1000 or any(ord(c) < 33 or ord(c) > 126 for c in key):
            raise ValueError('Enter a valid API key without spaces, or leave it blank to disconnect.')
        if run_lock.locked():
            raise HTTPException(409, 'Wait for the current preparation before changing the key.')
        model_state.update(key=key, verified=False, last_error='')
        return model_status()

    def generate_selected(payload):
        if not model_state['key']:
            raise HTTPException(409, 'Meta AI is not connected. Add an API key in Memory & connections.')
        if not isinstance(payload, dict) or payload.get('consent') is not True:
            raise ValueError('Approve sending the selected material to Meta before generating.')
        ids = payload.get('source_ids')
        if not isinstance(ids, list) or not 1 <= len(ids) <= 4 or any(not isinstance(i, str) for i in ids) or len(set(ids)) != len(ids):
            raise ValueError('Choose one to four distinct source IDs.')
        if not run_lock.acquire(blocking=False):
            raise HTTPException(409, 'A preparation is already running.')
        try:
            saved = {s['id']: s for s in repo.snapshot()['sources']}
            if any(i not in saved for i in ids):
                raise ValueError('A selected source is no longer available. Reload and select again.')
            revisions = payload.get('source_revisions')
            if not isinstance(revisions, dict) or any(type(revisions.get(i)) is not int or revisions[i] != saved[i]['revision'] for i in ids):
                raise ValueError('Selected material changed or approval is incomplete. Reload its preview and approve again.')
            hashes = payload.get('source_hashes')
            if not isinstance(hashes, dict) or any(not isinstance(hashes.get(i), str) or hashes[i] != saved[i]['content_hash'] for i in ids):
                raise ValueError('Selected material no longer matches your preview. Reload and approve again.')
            sources = [saved[i] for i in ids]
            if sources[0]['kind'] not in {'lecture', 'assignment', 'project_note', 'mail'}:
                raise ValueError('Start with a lecture, assignment, or project note.')
            try:
                result = MetaClient(model_state['key']).generate(sources)
            except ModelError as exc:
                model_state['last_error'] = str(exc)
                raise HTTPException(502, str(exc)) from None
            draft = {**result, 'id': uuid4().hex, 'title': sources[0]['title'] + ' · Muse Spark'}
            repo.save_generated_draft(draft, sources)
            model_state.update(verified=True, last_error='')
            return {'draft_id': draft['id'], 'model': MODEL}
        finally:
            run_lock.release()

    @app.post('/api/model/generate')
    async def model_generate(request: Request):
        if not model_state['key']:
            raise HTTPException(409, 'Meta AI is not connected. Add an API key in Memory & connections.')
        payload = json.loads(await read_limited(request))
        return await asyncio.to_thread(generate_selected, payload)

    @app.post('/api/agent/demo')
    def agent_demo_load(stage: str = 'initial'):
        if stage not in {'initial', 'update'}:
            raise ValueError('Choose initial or update demo stage.')
        if run_lock.locked():
            raise HTTPException(409, 'Wait for the current preparation.')
        return {**repo.import_items(agent_demo(stage)), **check()}

    def run_agent(payload):
        if not model_state['key']:
            raise HTTPException(409, 'Add a replacement API key in Memory & connections first.')
        if not isinstance(payload, dict) or payload.get('consent') is not True:
            raise ValueError('Approve the selected sources and task progress before running.')
        ids = payload.get('source_ids')
        if not isinstance(ids, list) or not 1 <= len(ids) <= 4 or any(not isinstance(i, str) for i in ids) or len(set(ids)) != len(ids):
            raise ValueError('Select one to four distinct sources.')
        if not run_lock.acquire(blocking=False):
            raise HTTPException(409, 'A preparation is already running.')
        try:
            by_id = {s['id']: s for s in repo.snapshot()['sources']}
            revisions, hashes = payload.get('source_revisions'), payload.get('source_hashes')
            if not isinstance(revisions, dict) or not isinstance(hashes, dict) or any(i not in by_id or type(revisions.get(i)) is not int or revisions[i] != by_id[i]['revision'] or hashes.get(i) != by_id[i]['content_hash'] for i in ids):
                raise ValueError('Material changed or approval is incomplete. Reload the preview and approve again.')
            try:
                result = AgentRunner(repo, MetaClient(model_state['key'])).run([by_id[i] for i in ids])
            except ModelError as exc:
                model_state['last_error'] = str(exc)
                raise HTTPException(502, str(exc)) from None
            if result['status'] == 'completed':
                model_state.update(verified=True, last_error='')
            return result
        finally:
            run_lock.release()

    @app.post('/api/agent/run')
    async def agent_run(request: Request):
        payload = json.loads(await read_limited(request))
        return await asyncio.to_thread(run_agent, payload)

    frontend = ROOT / 'frontend' / 'dist'
    if frontend.exists():
        app.mount('/', StaticFiles(directory=frontend, html=True), name='ui')
    return app


app = create_app(Settings(data_dir=ROOT / '.local', run_scheduler=True))
