# Host Interaction Adapters

Select interactions from capabilities and the current host instructions, never from
a filesystem path. The adapter is a presentation layer: the lesson workflow,
permission gate, learner model, and evidence rules stay the same on every host.

## Permission and quiz prompts

For a permission request or multiple-choice question (MCQ), prefer a native,
single-choice picker when the current host exposes one:

- In Claude Code, prefer `AskUserQuestion` when available.
- In Codex, prefer `ask_user_question` when available.
- If that named tool is unavailable but the host exposes an equivalent
  single-choice interaction tool, use that equivalent.
- If no picker exists, use a plain-text fallback: present numbered choices, ask
  the learner to reply with the number or choice text, and continue the lesson.
  Do not fail a lesson because an interaction tool is absent.

Use the same prompt content in every presentation: quiz stem, options, correct
answer, feedback, and the resulting evidence type and weight. A native picker
changes only rendering, not quiz semantics.

## Context discovery

Global-context discovery remains capability-based and permission-gated. Only after
the learner grants the permission defined in `privacy.md`, inspect known global
sources that the current environment can actually access. Do not infer access or
consent from a host name, a filesystem path, or context already supplied by the
host. If access is unavailable, use onboarding and shared learner state.
