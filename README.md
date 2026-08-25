# Adaptive Tutor

## What it is

Adaptive Tutor is a portable Agent Skills pack for evidence-driven, personalized
tutoring. It contains `adaptive-tutor`, which runs the lesson workflow, and
`learn-verify`, which verifies uncertain or material factual claims before they
are taught as fact. V1 is terminal-native and works with Claude Code and Codex.

## Why it differs from a normal AI tutor

The tutor calibrates rather than trusting a claimed level, builds a dynamic
prerequisite map, teaches one unresolved node at a time, and asks for explanation,
application, or transfer evidence before advancing mastery. A correct multiple
choice answer or self-report alone cannot prove higher mastery. It records hint
dependence and contradictions so the next lesson can revisit weak foundations.

## Privacy and permission

Before actively reading global Claude/Codex context or memory, Adaptive Tutor asks
for explicit permission. `allow_once` applies only to the current learning
session; `allow_and_remember` persists only that permission decision; and `deny`
means it does not read global context and instead uses onboarding plus learner
state. Supplied conversation/project context does not authorize opening more
global files. Context and self-report are provisional personalization signals,
never proof of mastery, and unrelated or sensitive data is not copied into learner
storage.

## How memory stays cost-effective

The shared store has three tiers: a compact learner profile, domain-scoped mastery
files loaded only when relevant, and cold session archives that are not loaded by
default. Working evidence stays in the active lesson. At semantic checkpoints—such
as completing a concept, correcting a misconception, repeating a preference, or
ending a lesson—the tutor writes a bounded JSON delta. The deterministic merge
script validates, gates, and merges only eligible changes instead of rewriting
memory after every prompt.

## Install with npx skills

Replace `<owner>/<repo>` with this repository's GitHub slug. The common `skills`
CLI installs Agent Skills into agent-specific locations; let it do that routing.

```bash
npx skills add <owner>/<repo> -g --all
npx skills add <owner>/<repo> --list
```

The second command lists the available `adaptive-tutor` and `learn-verify` skills
without installing them. To install a local checkout while developing, the
verified CLI command is:

```bash
npx skills add . --list
```

For a noninteractive copied Codex install, use:

```bash
npx skills add . -g --copy --agent codex --skill '*' -y
```

Do not manually copy the learner store into Claude or Codex skill directories.
Those are installation locations; the learner store is shared local state.

## Claude Code usage

Install through `npx skills`, then ask Claude Code to teach, help you study, or
practice a topic. The `adaptive-tutor` skill requests the context permission
before any active global-context read, uses native choice prompts when available,
and invokes `learn-verify` for uncertain, current, niche, contested, or materially
important teaching claims.

## Codex usage

Install through `npx skills`, then ask Codex to teach, explain, quiz, or help you
practice a topic. It follows the same portable workflow, permission gate, learner
state, and evidence standards as Claude Code; only the host's prompt rendering may
differ.

## Shared local learner state

By default, learner state is local to `~/.adaptive-tutor/`:

- `LEARNER.yaml` is the compact profile and persisted consent decision.
- `mastery/<domain>.yaml` holds a domain-specific mastery index.
- `sessions/YYYY-MM-DD-topic.md` is a cold session archive.

This location is deliberately outside agent-specific skill directories, so Claude
Code and Codex use the same learner history on the same machine. During a semantic
checkpoint, create the bounded delta in a temporary or current-workspace location
and run:

```bash
python <skill-dir>/scripts/merge_delta.py --delta <checkpoint-delta.json>
```

Delete the temporary delta only after a successful merge; retain it if merging
fails so it can be diagnosed or retried.

## What V1 does not do

V1 does not provide a web UI, synchronise learner data across machines, treat
global context as mastery proof, persist every turn, or import external learner
profiles through claim verification. It does not bypass the context-permission
gate.

## Development/tests

Run from the repository root:

```bash
python -m unittest discover -s tests -v
python -m compileall skills tests
python skills/adaptive-tutor/scripts/merge_delta.py --help
npx skills add . --list
```

The packaging tests also prove that each runtime file named by
`adaptive-tutor/SKILL.md` is included inside that skill and that the merge CLI can
run from an arbitrary current working directory.

## Third-party attribution

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The project adapts ideas and
may adapt portions of skill text from `vasanthsreeram/Alvarmethod` under its MIT
license; the notice records the retrieved revision and attribution requirements.
