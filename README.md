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

All source data, profile, task progress and prepared drafts persist in `.local/sidekick.db`. The database is owner-readable/writable; it is not encrypted. No API credentials are configured. Gmail, Meta generation and live Canvas are not connected. CPP currently requires administrator approval for Canvas access. Sample worked answers are prewritten and labeled. HTML is inert; embedded Markdown images are omitted and the app blocks external media with CSP. Opening a chosen HTTPS source link is a user action.

Settings can enable 9 AM America/Los_Angeles preparation of saved material. The service must be running. It catches up after a missed morning. This does not fetch accounts or install a background system job. Nothing is sent, submitted, or marked complete automatically. Source deletion affects that selected source and dependent local records only.

This is an early prototype, not the completed autonomous companion or a security-audited public service. Do not expose its port publicly. No public deployment was made.
