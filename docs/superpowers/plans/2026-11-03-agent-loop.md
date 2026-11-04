# Sidekick agent loop implementation plan

> For agentic workers: use executing-plans; test before production changes.

Goal: implement the approved observe/compare/reason/prepare/verify/remember workflow across school and projects.
Architecture: retain the existing local FastAPI/SQLite/React application and feature branch. A bounded Meta planner selects at most two source-grounded preparation actions; the executor generates and validates drafts, then commits the run and checkpoint atomically. No external account actions.
Spec: ../../../../outputs/Sidekick_Agent_Focus_2026-10-31.md (approved product direction; implementation choices delegated by Kevin).

Global constraints: synthetic first live test; never use the key exposed in chat; no personal paid usage authorized; no background model schedule; max three calls per run; no automatic retries; selected exact source revisions/hashes only; preserve pre-event history; no publish or submit; no file deletion.

Task 1: agent engine and persistence
- Write failing tests for new/changed/unchanged/progress changes, persistent checkpoint and no duplicate calls, source race rollback, invalid plans and restricted sources.
- Add backend/app/agent.py: fingerprint(sources,tasks), changes(previous,current), AgentRunner(repo,client).run(sources).
- Add MetaClient.plan(sources,tasks,changes) using strict structured output, <=2 preparation actions, validated IDs and no completed-task work.
- Repository persists successful run/drafts atomically after checking current source hashes and task states. Failed runs are visible but never advance checkpoint.
- Run backend suite; commit exact files.

Task 2: API, user interface, synthetic scenario
- Write failing API and UI tests proving exact consent, missing key, duplicate skip, visible plan/output and disconnect.
- Add /api/agent/run, agent state and /api/agent/demo?stage=initial|update. Use existing shared run lock. No scheduled AI.
- Add Today AgentPanel with explicit source selection/preview, consent, bounded-run button, changes, evidence-linked priorities, output links, audit and stale/failure labels. Existing tasks retain completion state.
- Synthetic school/project fixture uses fixed Nov 2026 dates; update changes deadline and meeting requirement under stable IDs.
- Run full backend/frontend suites and production build; commit exact files.

Task 3: live verification and submission preparation
- Open local app, user supplies replacement key personally. Verify a real synthetic agent run, changed-source run, completion and no-change skip. Check Meta billing after use.
- Prepare honest README, event-work manifest, demo script and submission draft. Do not publish or submit.
- Fresh reviewer checks diff, race/privacy/cost safeguards, provenance and claims. Fix important findings with failing tests first. Record remaining blockers accurately.

Review focus: changed source or task during provider call; malformed plan/content; duplicate requests; restricted or unselected source leakage; stale historical run displayed as current.

Execution notes: user already requested autonomous inline implementation and delegated routine choices. Reuse clean feat/local-demo checkout per developer preference. Keep this plan and evidence; no workspace cleanup/deletion.
