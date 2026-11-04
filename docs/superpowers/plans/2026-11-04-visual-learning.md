# Visual learning implementation plan

Goal: explain uploaded material visually and in concise beginner-friendly steps, using Meta Muse Spark. Preserve the broad work-partner purpose; this is a School preparation improvement.

Approach: preserve original PDFs privately in SQLite and lazily render selected pages using PDFium/Pillow. Show original slides and explicitly approve at most four page images per request. Muse Spark receives text plus selected page images via its documented Chat Completions image_url blocks. Ask for short teaching steps and validated structured diagram nodes/edges; React renders interactive SVG concept diagrams. No arbitrary model SVG/HTML, remote image loads, or automatic extra image-generation calls. Accurate source diagrams plus concept sketches are preferred over decorative raster generation.

Task 1: PDF visual preservation and scope (TDD)
- Store PDF bytes atomically with source/revision hash. Support scanned PDFs as visual sources. Bind stored documents to source identity/hash, and expose only visible workspace pages behind existing local session checks.
- Lazy JPEG rendering (longest side <=1400 px), global PDFium lock, one page at a time; no network resource fetch. At most four approved page images across selected sources per call; preserve source hashes/revisions and include pages in consent preview.
- Existing text-only imports remain labeled; re-import or recover the exact original locally when possible. Never invent missing diagrams.

Task 2: model visual explanations (TDD)
- Generate 3–6 short learning steps, small examples and up to two source-grounded concept diagrams. Validate node/edge IDs, bounds, labels, source references and selected page citations. Reject malformed visual results before persistence; legacy text-only drafts still render.
- Add image blocks only for explicitly selected pages; text-only path remains compatible. No image input is silently enabled for old approvals. Keep provider errors sanitized and no auto retries.

Task 3: teaching view and direct School action (TDD)
- School material has Explain with Meta, which opens explicit source/page review and one bounded generation call. Today agent retains its plan/execute loop.
- Source viewer shows original page previews; explanation viewer shows short step cards, examples, interactive concept sketches and source references. Keep ordinary Markdown external images blocked.
- Test scope, rendering, missing originals, unsafe SVG/HTML, and invalid diagrams. Full suites/build, fresh review, browser proof using synthetic fixtures; no private lecture transmission or publication without scope approval.

The user's routine-choice delegation remains active. No new model call is required to build/verify this revision. Live verification depends on configured key, credits and user-approved source/page scope.
