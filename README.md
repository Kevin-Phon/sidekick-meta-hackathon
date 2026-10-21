# Sidekick — private local companion prototype

A preparatory demo for Kevin's AI companion idea. Competition eligibility for early prototype code remains unverified.

## Run on this Mac

From this directory:

```sh
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8765
```

Open http://127.0.0.1:8765. Stop with Ctrl+C. No login daemon is installed. It only listens on loopback.

## Set up elsewhere

Use Python 3.12+ and Node 22.12+ (tested with Python 3.12 and Node 24).

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
cd frontend
npm ci
npm run build
cd ..
```

Then use the run command above. For tests: `.venv/bin/python -m pytest -q`, and inside frontend `npm test -- --run` plus `npm run build`.

## Try it

Explore the sample day, open a worked homework draft, inspect its sources, download Markdown, mark a task complete, and reload. Projects accepts progress notes. Add material accepts selectable-text PDF, TXT, Markdown, and JSON. Imported course material receives a source outline or missing-input checklist. It does not receive invented AI answers.

JSON accepts an `items` array with title, body, kind (lecture/assignment/announcement/project_note/mail), optional provider_id, due_at with timezone, metadata.course/project and assessment restriction flags. Reusing an explicit connection_id/provider_id updates that source and invalidates its old derived drafts. File imports use content/context identity: changed files become separate snapshots; delete an obsolete snapshot individually in Settings. Identical imports are idempotent.

## Boundaries and storage

All source data, profile, task progress and prepared drafts persist in `.local/sidekick.db`. The database is owner-readable/writable; it is not encrypted. No API credential is bundled. Gmail and live Canvas are not connected. Muse Spark generation is implemented but live verification needs your key and available API credits. CPP currently requires administrator approval for Canvas access. Sample worked answers are prewritten and labeled. HTML is inert; embedded Markdown images are omitted and the app blocks external media with CSP. Opening a chosen HTTPS source link is a user action.

Settings can enable 9 AM America/Los_Angeles preparation of saved material. The service must be running. It catches up after a missed morning. This does not fetch accounts or install a background system job. Nothing is sent, submitted, or marked complete automatically. Source deletion affects that selected source and dependent local records only.

This is an early prototype, not the completed autonomous companion or a security-audited public service. Do not expose its port publicly. No public deployment was made.

## Muse Spark connection (October 21)

Open Memory & connections → Muse Spark. Enter a Meta Model API key into the password field and click Use key for this session. The server holds it only in memory; no key is written to this project or browser storage. You can instead supply MODEL_API_KEY through the server process environment. Disconnect clears its active key. Do not paste credentials in chat or Git.

Select one source and inspect its exact text, title, ID and revision. Approve sending that material to Meta, then Generate with Muse Spark. The app uses muse-spark-1.3 Standard via https://api.meta.ai/v1/chat/completions with a JSON schema. No profile, other sources, URLs or account data are fetched/sent automatically. A successful live generation changes status from Key set/unverified to Verified and saves a labeled draft. Key setup alone does not verify access or credits.

Requests contain at most four sources/32KB total (the UI currently selects one), cap model completion at 4,000 tokens, and cap response at 1MB. HTTP inactivity timeout is 45 seconds and connection timeout10seconds; a slow continuous response can last longer. No automatic retries or paid scheduled calls. Check credits/billing before trying. Provider errors are sanitized; source revisions and content fingerprints must match approval, and changed sources block persistence. A valid citation identity is not proof every generated claim is correct: review the draft.

Official references: https://dev.meta.ai/docs/models, https://dev.meta.ai/docs/structured-output, https://dev.meta.ai/docs/protocols/chat-completions.
