# Sidekick — final submission draft for review

Team/project name: Sidekick
Track: Indie Developer
Theme: Build for Your World
Public repository: https://github.com/Kevin-Phon/sidekick-meta-hackathon
Demo video/player: https://kevin-phon.github.io/sidekick-meta-hackathon/
Direct MP4: https://kevin-phon.github.io/sidekick-meta-hackathon/demo/Sidekick-Demo.mp4

## Project description

Sidekick is an AI work partner that helps keep school, projects and messages together. I want it to feel like a second brain on my side: understand the material I choose to share, suggest what matters next, and prepare useful work for me to review.

The working agent compares saved source revisions and task progress with its previous state. Muse Spark chooses up to two useful preparation actions. Sidekick creates local drafts, validates their source references, checks that the inputs have not changed, and saves the outputs and checkpoint together. Repeating unchanged context skips the model instead of generating duplicate work. Source changes mark old plans as historical.

School supports original PDF slide previews and approved page-image input for short teaching steps, examples and interactive concept diagrams. Mail supports Google sign-in with read-only Gmail access, a manually triggered preview of five recent inbox messages, and source-approved summaries, suggested priorities and next steps. Reply suggestions remain local drafts. Today gathers priorities and prepared work; Projects brings together project-related context.

This is a local prototype. Gmail checks and agent runs are triggered by the user; continuous monitoring and Canvas integration are not implemented. It does not send mail or submit coursework. The public demo uses fictional sources. Actual course material, real emails, account credentials and the private database are excluded from the public repository and video.

The October 20–21 preparatory prototype is disclosed. The November 3–4 event work includes the bounded compare/plan/prepare/verify/remember agent, simplified workspaces, visual learning and Gmail connection/preview. See docs/EVENT_WORK.md for the distinction; organizer eligibility remains unconfirmed.

## Use of Meta products

Sidekick uses Muse Spark 1.3 Standard through Meta Model API Chat Completions with structured JSON output. The planning call selects source-linked priorities and up to two local preparation actions; each preparation uses a separate bounded request. Code validates the action targets, source revisions, content hashes and diagram structures before saving results. Agent runs make at most three requests, with no automatic retries. Direct school or mail preparation makes one request.

For visual lessons, the model receives approved extracted text plus up to four explicitly selected PDF page images. Muse Spark produces teaching steps and concept nodes/edges; Sidekick renders interactive SVG diagrams. It does not use a separate image-generation model. Real model calls verified the agent workflow, visual lesson generation and an approved mail summary. Muse Code and other partner tools are not claimed as used.

## Why Meta's models matter

Muse Spark provides the reasoning that turns source changes into a useful preparation plan and produces explanations, project briefs and message recommendations. Its image understanding lets the app include approved lecture diagrams, rather than losing them during text extraction. Structured output gives the backend a format it can validate before executing local draft actions. The model supports the work-partner behavior; it is more than a static dashboard or a collection of prewritten study notes. Suggestions and factual accuracy still require human review.

## Final review items

- The published video is 2:38 and demonstrates the November 3 agent using fictional sources; it does not depict the later private visual/Gmail tests. It is an edited screenshot walkthrough with synthetic narration.
- Automated verification: 81 backend tests, 15 frontend tests and supported Node 24 production build passed. Mocked provider tests and real live checks are documented separately.
- Confirm contributor attribution and answer the form's personal feedback/survey questions truthfully. Do not claim comparisons or tool use that did not occur.
- The submission form asks permission for Meta/Cerebral Valley to use, publish, share and promote submitted materials. Kevin must review that choice and approve the final submission.
- After actual submission, disconnect model/Gmail access and stop the service as requested. Submission itself does not do this automatically.

Status: prepared for review; not submitted.
