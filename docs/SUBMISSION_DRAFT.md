# Sidekick — submission draft for Kevin's review

One-line description: An AI work partner that turns approved school and project updates into evidence-linked priorities and prepared drafts, while remembering progress.

Problem: Important information arrives in different places. A deadline change or meeting request affects what a student and project teammate should work on next. Keeping that context together takes attention and repeated instructions.

Solution: Sidekick compares saved source revisions and task progress, asks Muse Spark to choose a bounded preparation plan, creates relevant local drafts, checks the results against the current source state, and remembers the run. Repeated unchanged context uses zero model calls. A changed source marks historical plans stale.

Meta integration: Muse Spark 1.3 through Meta Model API Chat Completions with structured output for planning and generated preparation. The application validates action targets and source references and limits execution to at most two draft actions after one planning call.

Event-built work: See EVENT_WORK.md. Preserve the October 20–21 prototype disclosure.

Current access: Imported or fictional saved snapshots; live Gmail and Canvas are not connected. Human-triggered source updates and agent runs are labeled. External sends/submissions are not performed.

Published materials and remaining review:
- Public repository: https://github.com/Kevin-Phon/sidekick-meta-hackathon
- Demo player: https://kevin-phon.github.io/sidekick-meta-hackathon/
- Direct MP4: https://kevin-phon.github.io/sidekick-meta-hackathon/demo/Sidekick-Demo.mp4 (2:02 edited real screenshots with synthetic narration). Public player loaded with correct metadata and no media error.
- Kevin's final review, contributor attribution, and submission approval.
- Live synthetic verification completed November 3: initial run (3 calls), changed-source run (3 calls), progress-aware run (2 calls); unchanged repeats skipped Meta. Local checks: 49 backend tests, 7 frontend tests, production build passed. No live account connector or continuous observation is claimed.

After submission: Disconnect the model and stop the service. Verify no new API calls can run; no background AI schedule exists in this build. Submission alone does not disable the API account.
