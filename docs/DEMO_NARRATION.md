# Narration for a short screen walkthrough

Sidekick is an AI partner on my side. I want it to keep track of school, projects, messages, and the work I need to do next. Study guides are one thing it can prepare, but the main idea is having a partner that keeps the context together and helps me move forward.

This demo uses four clearly fictional saved sources. There is a lecture, a practice assignment, a project note, and a saved message. These are snapshots. I am not claiming that Gmail or Canvas is connected yet. I choose what Sidekick can send to Meta, and it can only prepare local drafts within that scope.

The new agent workflow compares the current sources with its last saved state. Muse Spark decides what needs attention and chooses up to two preparation actions. Sidekick carries out those actions, checks the source references and current input state, and saves the plan and outputs together.

Here is a real result after an update. The practice deadline moved from November fifth to November fourth at noon Pacific. The project check-in is at three that afternoon, and now asks for an error-state demonstration. Sidekick puts the earlier school deadline first, while keeping the project requirement visible.

The prepared school draft explains the question, uses the selected lecture, works through the set operations, and checks the answer. The project brief summarizes recorded progress, the blocker, and what to bring to the meeting. It separates source facts from suggestions. Both were generated through the Meta Model API and still need my review.

When I mark the fictional school task done, Sidekick remembers that progress and reassesses the remaining work. If I run it again with the same sources and progress, it skips the model. That means no duplicate outputs and no extra API calls for an unchanged run.

The event build adds this agent workflow to an earlier local prototype. It does not yet watch every app or work continuously in the background. The next step is approved live connectors. For now, the working core is: notice a change, decide what matters, prepare useful work, verify, and remember.
