import asyncio
import hashlib
import json
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
from app.repository import Repository
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
        return {**saved, 'connections': [
            {'id': 'imports', 'name': 'Course & project files', 'status': 'local', 'detail': 'Saved snapshots. Import new material to update them.'},
            {'id': 'canvas', 'name': 'Canvas', 'status': 'blocked', 'detail': 'CPP requires an administrator-approved connection. Import course files for now.'},
            {'id': 'gmail', 'name': 'Gmail', 'status': 'not_connected', 'detail': 'Independent app authorization is not configured.'},
            {'id': 'meta', 'name': 'Meta AI', 'status': 'not_connected', 'detail': 'No API credential or live model request has been configured in this app.'}],
            'next_run': next_daily_run(datetime.now(timezone.utc)).isoformat(),
            'mode': 'sample' if any(x['metadata'].get('demo') for x in saved['sources']) else 'local',
            'eligibility': 'Preparatory prototype. Hackathon build-window eligibility is not yet verified.'}

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
    async def import_file(request: Request, filename: str, kind: str = 'lecture', title: str = '', course: str = '', due_at: str = ''):
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
                      'body': text, 'due_at': due_at or None, 'metadata': {'course': course, 'filename': filename}}]
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

    @app.patch('/api/profile')
    async def profile(request: Request):
        patch = json.loads(await read_limited(request))
        if not isinstance(patch, dict) or any(not isinstance(patch[x], str) or len(patch[x]) > 3000 for x in ('name', 'goal') if x in patch):
            raise ValueError('Name and goals must be text under 3,000 characters.')
        if 'daily_enabled' in patch and not isinstance(patch['daily_enabled'], bool):
            raise ValueError('Daily preparation must be on or off.')
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

    @app.post('/api/model/generate')
    def model_unavailable():
        raise HTTPException(409, 'Meta AI is not connected. Sample answers are prewritten; source outlines are not AI generations.')

    frontend = ROOT / 'frontend' / 'dist'
    if frontend.exists():
        app.mount('/', StaticFiles(directory=frontend, html=True), name='ui')
    return app


app = create_app(Settings(data_dir=ROOT / '.local', run_scheduler=True))
