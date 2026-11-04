# Clean workspace implementation plan

Goal: implement Kevin's simpler School/Mail → Projects → Today flow using the existing React/FastAPI stack. User delegated recommendations and implementation; preserve old content in an archived workspace rather than deleting files or records. Initial dashboard has no fictional examples or prefilled work. Gmail connection must be described honestly; no OAuth setup exists yet.

Design: School is the upload library, Mail offers a connection setup explanation and saved-message import, Projects derives a context view from source metadata and project notes, Today shows suggested priorities and prepared output. Keep agent consent in a review dialog, technical activity collapsed, sample controls in settings only. Existing model API/key flow remains. Add email reply drafts as bounded preparation actions; never send messages.

Task 1 — workspace isolation and mail preparation (TDD)
- Repository creates/selects an active workspace; old records remain intact. New imports receive workspace identity. Snapshot filters sources/tasks/drafts; API agent history filters to visible sources. Settings offers archived workspace selection.
- Add mail_reply type and source-grounded email generation; model planner may choose mail actions. Local imported messages get source outlines, never invented AI replies.
- Test blank workspace, scoped imports, restoring archive, no cross-workspace source leak, mail drafts and no external send.

Task 2 — simplify UI (TDD)
- Replace busy dashboard with distinct empty states and small source-backed sections. School-only material import; Mail imports saved email and shows explicit Gmail setup status. Projects aggregates related course/mail/project sources; Today recommendations/prepared output only, review-sources dialog for agent runs.
- Settings holds profile, workspace selection/start-fresh, source management, model setup, optional demo controls. Preserve all prior key and rendering protections.
- Test all four empty states, add material flow, mail connection explanation, saved mail reply, and clean agent source approval.

Task 3 — verify and review
- Run full backend/frontend suite and build; inspect the actual browser at empty state and after a synthetic source import in a separate test workspace.
- Fresh code reviewer checks scope isolation, races, privacy, misleading Gmail status, task filtering and source consent.
- Prepare screenshots; update public code/demo only after the new behavior is verified. Keep old demo labeled as earlier version until replaced. No paid model call without checking current credits and approved source packet.
