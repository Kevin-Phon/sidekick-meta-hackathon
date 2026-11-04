# Sidekick — your AI work partner

Sidekick turns approved school and project updates into suggested priorities and prepared work. It compares saved source revisions and task progress, asks Muse Spark to select up to two local preparation actions, creates drafts, verifies current inputs, and remembers the result.

## Watch the demo

[Watch the 2:38 Sidekick walkthrough](https://kevin-phon.github.io/sidekick-meta-hackathon/) · [Download the video](https://kevin-phon.github.io/sidekick-meta-hackathon/demo/Sidekick-Demo.mp4)

The edited walkthrough introduces the cleaned interface, then labels earlier successful agent validation footage. It uses actual app screenshots from successful live Muse Spark runs with fictional source data, plus a synthetic system narrator. It is not a continuous screen recording. It shows changed priorities, generated school/project preparation, and saved progress. No private account data or credentials appear.

## November 3 event build

The agent workflow is new competition-period work built on an October 20–21 preparatory prototype. See [event-work disclosure](docs/EVENT_WORK.md), [demo script](docs/DEMO_SCRIPT.md), and [submission draft](docs/SUBMISSION_DRAFT.md). Eligibility remains the organizers' decision.

Run locally using the instructions below. Start with an empty workspace: upload a lecture, assignment, or project brief in School; paste a saved message in Mail. Projects collects material with a project label, project-note type, or project-related title. Today brings together suggested priorities and prepared work. Choose Prepare next steps, review up to four exact sources, approve the scope, and run Sidekick. Suggestions, worked drafts and mail reply drafts need review; nothing is sent or submitted.

Muse Spark setup is in Memory & connections. Use a fresh unshared key in the password field. One agent run makes at most three API requests (one plan and up to two preparations); unchanged input skips the model. The everyday dashboard has no seeded examples. Optional samples live under Memory & connections → Saved sources and sample workspace. Start clean workspace preserves previous material and lets you switch back. New installations have no prefilled personal profile.

Canvas remains file-import only. Gmail now has a session-only read-only Google OAuth connection; a real account connection was verified November 4 after developer setup and the user’s Google approval. Imports and manually triggered runs demonstrate the bounded agent core; continuous background observation is future work. When Google developer setup is configured, Connect Gmail opens Google sign-in directly. Without it, the app explains the one-time setup. Saved-email import also works. The local 9 AM scheduler only makes local source outlines and never calls Meta. Never expose this app's port to the internet.

## Visual learning (November 4)

In School, choose **Explain with Meta** on a lecture or assignment. Review the extracted text and select up to four PDF page images across the approved sources. The original slide viewer stays local; only the chosen page images and approved source packet are included in that model request. This makes diagram-only and scanned pages available to Muse Spark alongside the text. One direct explanation makes one API request.

Lessons show a short overview, beginner-friendly steps with small examples, and up to two interactive concept diagrams when useful. Muse Spark supplies validated nodes and connections; Sidekick draws those as SVG. This is a teaching sketch, not a separate image-generation service or an exact reproduction of the lecture. Click a concept to read its explanation, and compare it with the original slide. Image interpretation and connections still need review.

Original PDFs are stored privately in the local SQLite database, bound to the source content hash. Older text-only imports need the original PDF added again. Local rendering is bounded to 1,400 pixels and 400 KB per page image; page images are sent only with explicit approval. Automated tests cover image payloads, output validation, source/version binding, and the lesson interface. One live visual generation was verified November 4 using approved lecture text and two selected page images: two interactive concept diagrams and five teaching steps were saved and survived reload. The private source and result are not published. Extended notes are collapsed by default. The published video demonstrates the earlier agent workflow.

## Gmail sign-in setup

1. Create a Google Cloud project, enable Gmail API, and configure Google Auth Platform for an External app in Testing mode. Add only your own account as a test user for development.
2. Create a **Web application** OAuth client with the authorized redirect URI `http://127.0.0.1:8765/oauth/google/callback`.
3. Open Sidekick at **http://127.0.0.1:8765** (the callback must use the same hostname), choose Mail → Connect Gmail, select the downloaded client JSON, and choose Use Google setup for this session. Alternatively set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in the server process environment. Keep downloaded credentials outside this repository.
4. Click Connect Gmail / Continue with Google, choose your account, and review Google's read-only Gmail permission. The flow verifies the Gmail profile and returns to Mail. Denial does not connect the account.

Client secrets and access tokens stay in server memory. No refresh token is requested; restart or Google access-token expiry requires reconnection. Connections are workspace-bound. Disconnect clears local access and attempts Google token revocation; provider failure is reported honestly. Sign-in uses short-lived single-use state, PKCE, a dedicated callback cookie, fixed endpoints/redirect, bounded provider responses, and sanitized errors. OAuth callback URLs are omitted from access logging.

**Connecting alone does not import messages.** In Mail, **Load 5 recent emails** fetches up to five inbox messages using read-only Gmail requests and saves bounded text snapshots locally. Refresh is manual; there is no background polling. Attachments, images, scripts and styles are omitted. Missing or oversized messages are reported as skipped; excerpts are labeled. Repeated imports preserve message identity; account/workspace identities are kept separate. Gmail read status stays unchanged.

Cards show sender, received/saved time and Gmail's Important label, which is not an AI importance judgment. Up to five most recent saved messages are displayed, with Gmail-flagged messages placed first within that set. **Summary & next steps** opens the exact-source review before one Muse Spark request. It produces a short summary, suggested priority/reason, next action and a reply draft only if useful. Nothing is sent. Meta setup/credits are required only for this recommendation step. Private message data stays out of the public repository and demo. Live import/recommendation verification is recorded separately; automated provider responses are mocked. Gmail read-only is a restricted scope; public distribution may require Google verification. This local testing setup is not a verified public OAuth app.

Official setup: [Google Gmail authorization](https://developers.google.com/workspace/gmail/api/auth/web-server), [Gmail scopes](https://developers.google.com/workspace/gmail/api/auth/scopes).

## Costs and stopping

Meta bills API usage. Free credits must be active; spend alerts are not hard limits. Check billing after use (it may lag). Disconnect in Memory & connections removes the active in-memory key and blocks subsequent API requests. Stop the server to stop the local service. After the hackathon submission Kevin intends to disconnect and stop the app; submission itself does not do that automatically. No recurring credit monitor is installed.

## Verification and provenance

Backend tests: `.venv/bin/python -m pytest -q`. Frontend: `npm test -- --run`, `npm run build` from `frontend/`. Test responses use mocked transport and are not proof of live inference. Live testing was separately performed November 3 with synthetic sources; see the accompanying verification report for exact outcomes.

The server stores saved sources, task state, generated drafts, and agent checkpoints/activity in `.local/sidekick.db`. API keys stay in process memory. Historical checkpoints support source comparisons; deleting a selected source removes its related agent memory/history and outputs. Generated references identify supplied sources but do not prove every factual statement correct. All prepared work needs review.

---

# Earlier prototype instructions and technical details

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

Explore the sample day, open a worked homework draft, inspect its sources, download Markdown, mark a task complete, and reload. Projects accepts progress notes. Add material accepts PDF (including image-only pages), TXT, Markdown, and JSON. Imported course material receives a source outline or missing-input checklist. It does not receive invented AI answers.

JSON accepts an `items` array with title, body, kind (lecture/assignment/announcement/project_note/mail), optional provider_id, due_at with timezone, metadata.course/project and assessment restriction flags. Reusing an explicit connection_id/provider_id updates that source and invalidates its old derived drafts. File imports use content/context identity: changed files become separate snapshots; delete an obsolete snapshot individually in Settings. Identical imports are idempotent.

## Boundaries and storage

All source data, original uploaded PDFs, profile, task progress and prepared drafts persist in `.local/sidekick.db`. The database is owner-readable/writable; it is not encrypted. No API credential is bundled. Gmail OAuth and manual inbox text snapshots are implemented; live Canvas is not implemented. Muse Spark generation is implemented but live verification needs your key and available API credits. CPP currently requires administrator approval for Canvas access. Sample worked answers are prewritten and labeled. HTML is inert; embedded Markdown images are omitted and the app blocks external media with CSP. Opening a chosen HTTPS source link is a user action.

Settings can enable 9 AM America/Los_Angeles preparation of saved material. The service must be running. It catches up after a missed morning. This does not fetch accounts or install a background system job. Nothing is sent, submitted, or marked complete automatically. Source deletion affects that selected source and dependent local records only.

This is an early prototype, not the completed autonomous companion or a security-audited public service. Do not expose its port publicly. No public deployment was made.

## Muse Spark connection (October 21)

Open Memory & connections → Muse Spark. Enter a Meta Model API key into the password field and click Use key for this session. The server holds it only in memory; no key is written to this project or browser storage. You can instead supply MODEL_API_KEY through the server process environment. Disconnect clears its active key. Do not paste credentials in chat or Git.

Select one source and inspect its exact text, title, ID and revision. Approve sending that material to Meta, then Generate with Muse Spark. The app uses muse-spark-1.3 Standard via https://api.meta.ai/v1/chat/completions with a JSON schema. No profile, other sources, URLs or account data are fetched/sent automatically. A successful live generation changes status from Key set/unverified to Verified and saves a labeled draft. Key setup alone does not verify access or credits.

Requests contain at most four sources/32KB total of serialized text, plus up to four explicitly approved PDF page images, cap model completion at 4,000 tokens, and cap response at 1MB. HTTP inactivity timeout is 45 seconds and connection timeout10seconds; a slow continuous response can last longer. No automatic retries or paid scheduled calls. Check credits/billing before trying. Provider errors are sanitized; source revisions and content fingerprints must match approval, and changed sources block persistence. A valid citation identity is not proof every generated claim is correct: review the draft.

Official references: https://dev.meta.ai/docs/models, https://dev.meta.ai/docs/structured-output, https://dev.meta.ai/docs/protocols/chat-completions.
