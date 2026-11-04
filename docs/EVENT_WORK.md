# Event work and prior prototype

Sidekick is a local AI work partner. Its long-term goal is to notice important updates across permitted school, projects and messages, prepare useful work, and remember progress.

## Before the event

Commits through 715867f (October 20–21) are preparatory work: local UI, imports, SQLite source/task/draft storage, sample templates, local scheduler, and the initial selected-source Meta adapter. These are not claimed as event-built.

## Built November 3, 2026

- `backend/app/agent.py`: compare prior source/task state, skip unchanged context, execute model-selected bounded preparation actions, verify current state, atomically store outputs and checkpoint, keep failure audit.
- `backend/app/agent_demo.py`: fictional school/project update scenario with stable identities and revisions.
- `backend/app/model.py`: structured Muse Spark planning with validated action targets; shared bounded HTTP transport.
- `backend/app/main.py`: consent-bound agent endpoint, synthetic update endpoint, historical/stale activity state.
- `frontend/src/components/AgentPanel.tsx` plus integration: selected-source preview, run consent, evidence-linked priorities, changed input state, prepared outputs, audit.
- `backend/app/repository.py`: selected-source withdrawal removes related new agent history/checkpoints/outputs.
- Agent tests and documentation for the event workflow.

Do not describe the entire codebase as created during the competition. Organizer interpretation of indie reuse remains unconfirmed.

## Demonstrated boundaries

Saved file snapshots and fictional sources exercise this workflow. Sidekick does not independently connect to Gmail or Canvas, continuously watch websites, submit assignments, send messages, or complete real project work outside the app. The model selects local preparation actions, and code validates and executes them. Content accuracy requires human review.

## November 3 interface revision

The dashboard now starts empty, with School uploads, saved messages in Mail, project context derived from those sources, and Today focused on priorities/prepared outputs. Agent source consent is in a dialog; optional sample controls live in Settings. Workspaces preserve archived sources rather than deleting data. New installs have no prefilled personal profile. Mail reply drafts are now a supported local preparation type, tested with mocked provider transport; this revision made no paid model requests. Gmail's connection entry honestly reports that Google OAuth setup is not configured.
