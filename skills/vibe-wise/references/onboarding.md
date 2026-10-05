# Minimal onboarding

Reuse answers already in the conversation. Explain in one sentence that the learner
shapes meaningful design decisions and Codex writes the agreed code. Notes stay in
the project's `.vibe-wise/`; recommend ignoring it without changing Git settings.

Ask at most one question at a time, only when the answer changes guidance:
- What are they building or changing, if no task was supplied?
- How familiar are they with this codebase or the relevant technology?
- What do they want to understand better, if no learning focus is apparent?

Accept “use defaults” or “skip setup” immediately: Normal frequency, open-ended
questions, AI writes code, and unknown experience recorded as Not specified.
Beginner gets grounding; intermediate gets interactions and tradeoffs; advanced
gets constraints and failure modes. Adapt to demonstrated familiarity per topic.
Do not confuse self-reported experience with demonstrated understanding.

Inspect existing code enough to map the parts the task touches. Record verified
paths and unknowns; do not invent a stack for an empty project. Use the templates
for missing state files. Preserve older preferences and labels without forcing a
schema migration or repeating completed onboarding.

For incomplete onboarding, ask only unresolved relevant questions. After a reset
(`Onboarding reset: pending`), use only answers supplied since reset; remove the
marker when complete. Backup notes are history, not current preferences. Record
known answers before yielding and mark onboarding complete once enough is known to
begin. Optional customization can happen later through ordinary conversation.
