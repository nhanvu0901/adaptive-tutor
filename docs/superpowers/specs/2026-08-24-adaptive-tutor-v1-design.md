# Adaptive Tutor Skill V1 — Design Specification

Date: 2026-08-24
Status: Proposed V1
Working repository name: `adaptive-tutor-skill`

## 1. Goal

Build a portable Agent Skill that runs across Claude Code and Codex, learns how to teach a specific user over time, and maintains a shared learner model without updating persistent memory on every prompt.

The tutor should know the learner before teaching, but must not treat remembered context as proof of mastery.

Core loop:

`PERMISSION -> CONTEXT -> CALIBRATE -> MAP -> TEACH -> PROVE -> DELTA -> GATE -> MERGE -> REVISIT`

## 2. V1 Principles

1. Ask permission before reading Claude/Codex global context or memory.
2. Explain that gathered context is used only for learning personalization.
3. If permission is denied or global context is unavailable, use a five-question onboarding fallback.
4. Remembered context is a hypothesis, not verified knowledge.
5. Verify topic-specific knowledge with adaptive calibration before skipping material.
6. Teach one meaningful node at a time rather than dumping a full textbook.
7. Require proof of understanding before promoting mastery.
8. Observe every interaction, but persist only meaningful learner-state changes.
9. Keep persistent memory small, structured, and replace state instead of appending forever.
10. Share one learner model across supported agents while keeping the learner's private state local by default.

## 3. V1 Scope

### Included

- Portable skill packaging for Claude Code and Codex.
- Cross-agent installation compatible with the Agent Skills ecosystem.
- Host-specific native quiz adapters.
- `learn-verify`-style fact verification before teaching uncertain claims.
- Permission-aware context discovery.
- Five-question onboarding fallback.
- Shared learner profile.
- Relevant-domain mastery index.
- Session archive.
- Evidence buffer.
- Semantic checkpoints.
- Memory delta generation.
- Memory gate and deterministic merge.
- Adaptive knowledge-map generation.
- Hint ladder.
- Mastery promotion based on evidence.

### Excluded from V1

- Central MCP memory server.
- Cloud account or hosted database.
- Automatic syncing between different physical machines.
- Heavy vector database or embedding index.
- Background daemon.
- Full spaced-repetition scheduler.
- Automatic modification of the user's Claude/Codex global files.

## 4. Privacy and Permission Model

Before reading any global Claude/Codex context, the tutor must ask:

> I can use your existing Claude/Codex context to understand your background, interests, and prior knowledge so I can personalize how I teach you. I will use this information only for learning personalization. May I read it?

V1 choices:

- `allow_once`
- `allow_and_remember`
- `deny`

Rules:

- No global read before consent.
- `allow_once` applies only to the current learning session.
- `allow_and_remember` stores only the permission decision, not a copy of the global context.
- `deny` causes immediate fallback to onboarding.
- Reading broader context does not authorize retention of unrelated information.
- Only learning-relevant signals may be retained: goals, interests, background, knowledge signals, learning preferences, and stable constraints.
- Sensitive or irrelevant material must be discarded.

## 5. Context Discovery

### Claude Code adapter

Potential sources, when permission allows and the host exposes them:

- user/global Claude instructions
- Claude memory available to the current agent
- current project instructions/context
- existing shared learner profile

### Codex adapter

Potential sources, when permission allows and the host exposes them:

- user/global Codex instructions
- Codex memory available to the current agent
- current project AGENTS instructions/context
- existing shared learner profile

### Context extraction rule

Convert discovered context into provisional learner signals, each with provenance and confidence.

Example:

```yaml
signal:
  concept: python
  claim: experienced
  confidence: 0.65
  provenance: codex_global_context
  verified: false
```

These signals may reduce onboarding and guide calibration, but never directly mark mastery as verified.

## 6. Five-Question Onboarding Fallback

Use only when sufficient global context is unavailable or the user denies access. Skip questions already answered by existing allowed context.

1. What do you want to be able to do after learning this topic?
2. What have you already studied, built, or used that is related to it?
3. What level do you think you are at, and what is one example that supports that estimate?
4. What subjects, projects, or interests should I use for examples when helpful?
5. How do you prefer to learn: pace, language, intuition vs. math, code vs. theory, and amount of practice?

Self-reported knowledge remains unverified until demonstrated.

## 7. Learner Model

V1 uses three storage tiers.

### Tier 1 — Learner Profile

Small and frequently loaded.

Suggested path:

`~/.adaptive-tutor/LEARNER.yaml`

Contains:

- learning goals
- stable interests
- background
- language
- teaching preferences
- durable strengths/weaknesses
- consent settings

Target size: small enough to read on every learning-session start.

### Tier 2 — Mastery Index

Suggested path:

`~/.adaptive-tutor/mastery/<domain>.yaml`

Read only the domain relevant to the current topic.

Concept states:

- `unknown`
- `exposed`
- `can_explain`
- `can_apply`
- `can_transfer`

Each concept may include:

```yaml
concept: attention
state: can_apply
confidence: 0.82
last_verified: 2026-08-24
evidence:
  strongest_type: transfer_exercise
  count: 3
```

### Tier 3 — Session Archive

Suggested path:

`~/.adaptive-tutor/sessions/YYYY-MM-DD-topic.md`

Cold storage for:

- lesson map
- important exercises
- mistakes
- hints used
- durable evidence
- final memory delta

Not loaded during normal tutoring unless evidence/history is needed.

## 8. Session Working State

Within an active lesson, maintain a lightweight in-context buffer:

```yaml
pending_evidence:
  - concept: scaled_dot_product_attention
    evidence_type: independent_explanation
    strength: medium
  - concept: attention
    evidence_type: unseen_application
    strength: strong
  - teaching_signal: matrix_visualization
    evidence_type: improved_performance
    strength: weak
```

This buffer is not persistent memory.

## 9. Semantic Checkpoints

Do not update persistent memory every prompt and do not use fixed message counts.

Run consolidation when one of these occurs:

- a concept node is completed
- a transfer exercise is completed
- a meaningful misconception is corrected
- a durable preference signal is repeated or strongly evidenced
- the lesson ends
- the user explicitly asks to save progress

A checkpoint may produce no persistent change.

## 10. Memory Optimization: Delta -> Gate -> Merge

### Step A — Delta generation

The active tutor already holds the current lesson context. At checkpoint time, it emits only state changes, not a prose summary and not a rewritten learner file.

Example:

```yaml
mastery_delta:
  attention:
    from: exposed
    to: can_apply
    confidence: 0.82
    evidence_type: unseen_application

misconception_delta:
  scaling_factor:
    status: corrected

preference_delta: null
```

### Step B — Memory gate

The gate decides whether a delta is worth persisting.

Persist when at least one is true:

- verified mastery state changed
- important misconception was discovered or corrected
- stable learning preference gained sufficient evidence
- goal or interest changed materially
- durable constraint changed
- information is clearly useful to future teaching

Discard low-value events such as individual wrong answers unless they support a durable state change.

### Step C — Deterministic merge

A non-LLM script validates the schema and merges the accepted delta into the stored state.

The script, not the LLM, controls file mutation.

Benefits:

- lower token usage
- less memory drift
- fewer accidental deletions
- easier testing
- reproducible state transitions
- easier rollback/debugging

## 11. Evidence and Confidence

Not all evidence has equal strength.

Suggested V1 evidence ladder:

1. self-report — very weak
2. recognition/MCQ — weak
3. recall — moderate
4. explanation — moderate
5. application — strong
6. transfer to unseen problem — very strong
7. repeated success across sessions — strongest durable evidence

Mastery promotion must consider:

- evidence type
- evidence strength
- repetition
- recency
- contradictions
- hint dependence

A single statement such as "I understand" never promotes mastery by itself.

## 12. Preference Learning

Do not convert one interaction into a permanent preference.

Use candidate-to-confirmed promotion.

Example:

```yaml
candidate_preferences:
  visual_for_systems:
    evidence_count: 2
    confidence: 0.55
```

After repeated supporting evidence:

```yaml
preferences:
  systems_concepts:
    strategy: visual_first
    confidence: 0.78
```

Strong explicit user instructions may be promoted immediately because they are direct durable preferences rather than inferred traits.

## 13. Calibration

Calibration has two modes.

### Context-rich mode

When learner context is substantial:

- identify uncertain prerequisites
- ask 1–3 high-information questions
- verify the knowledge boundary
- skip verified prerequisites

### Context-poor mode

When little is known:

- run onboarding if needed
- run an adaptive 5–10 question probe
- use binary-search-style prerequisite testing

The probe should stop as soon as the learning boundary is sufficiently clear.

## 14. Learning Map

Represent the topic as a dependency graph.

Example states:

- `verified`
- `probable`
- `weak`
- `untested`
- `goal`

Example:

```text
vectors        verified
matrices       verified
dot product    probable
softmax        weak
attention      untested
transformer    goal
```

The map is dynamic. If a learner fails a prerequisite, insert or reopen the necessary node.

## 15. Teaching Loop

For each active node:

1. connect to known context or learner interests when useful
2. teach the minimum explanation needed
3. ask the learner to retrieve/explain
4. ask an application question
5. use a transfer problem when appropriate
6. update working evidence
7. checkpoint when the node meaningfully resolves
8. continue to the next dependency

Never overload the learner with multiple new nodes when one unresolved prerequisite is sufficient to block progress.

## 16. Hint Ladder

When the learner struggles, escalate gradually:

1. restate the goal/question
2. small cue
3. targeted hint
4. partial scaffold
5. worked sub-example
6. full explanation

Track hint dependence as evidence. Solving only after heavy scaffolding should not be treated the same as independent success.

## 17. Native Quiz Adapter

Use each host's native interaction mechanism when available.

A thin adapter layer chooses the host capability while keeping quiz semantics shared.

The teaching core specifies:

```yaml
question:
options:
correct_answer:
feedback:
evidence_weight:
```

The host adapter renders it through Claude Code or Codex native interaction facilities when possible, otherwise it falls back to plain text.

MCQ is mainly for calibration/recognition. Higher mastery requires open explanation, application, or transfer.

## 18. Learn-Verify

Before teaching a factual claim that is uncertain, niche, current, or materially important:

1. turn it into a falsifiable claim
2. inspect an authoritative or primary source when tools permit
3. classify as:
   - `confirmed`
   - `qualified`
   - `contradicted`
   - `unknown`
4. teach only the verified/qualified form
5. do not present `unknown` as fact

V1 should reimplement or legally reuse this behavior depending on the upstream repository license.

## 19. Cross-Agent Packaging

Repository structure, proposed:

```text
adaptive-tutor-skill/
├── README.md
├── LICENSE
├── skills/
│   ├── adaptive-tutor/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   │   ├── learner-model.md
│   │   │   ├── pedagogy.md
│   │   │   ├── privacy.md
│   │   │   └── host-adapters.md
│   │   └── scripts/
│   │       ├── learner_store.py
│   │       ├── memory_gate.py
│   │       ├── merge_delta.py
│   │       └── validate_state.py
│   └── learn-verify/
│       └── SKILL.md
├── schemas/
│   ├── learner.schema.json
│   ├── mastery.schema.json
│   └── delta.schema.json
├── templates/
│   ├── LEARNER.yaml
│   └── mastery-domain.yaml
├── tests/
└── docs/
```

Installation should work with the common Agent Skills CLI, e.g. the eventual repository may be installable through `npx skills add <owner>/<repo>`.

## 20. Host Independence

The core tutor must not assume a specific Claude or Codex file path inside pedagogical logic.

Use host-adapter instructions:

```text
core tutor
   -> request global context permission
   -> host adapter discovers available sources
   -> normalized learner signals
   -> shared learner engine
```

If a host lacks a capability, degrade gracefully instead of failing the lesson.

## 21. Failure Handling

### Permission denied

Use onboarding and shared learner state only.

### Global source absent

Treat as normal; use onboarding as needed.

### Learner store absent

Create from template only after the user begins a learning flow.

### Corrupt learner state

Validate before merge; preserve the existing file and reject the delta rather than rewriting uncertain state.

### Contradictory evidence

Prefer recent verified performance over old inferred context. Lower confidence and probe again if needed.

### Uncertain factual teaching claim

Invoke verification when possible; otherwise label uncertainty and avoid presenting it as settled fact.

## 22. Testing Strategy

### Unit tests

- delta schema validation
- mastery-state transitions
- confidence clamping
- permission-state handling
- deterministic merge
- candidate preference promotion
- contradiction handling
- corrupt-file protection

### Scenario tests

1. first-time learner denies global context
2. first-time learner allows global context
3. returning learner with strong mastery evidence
4. remembered context incorrectly suggests mastery
5. learner changes explicit preference
6. one weak preference signal does not persist
7. repeated preference signals do persist
8. lesson produces no meaningful delta
9. transfer success promotes mastery
10. heavy-hint success does not over-promote mastery
11. Claude and Codex read the same shared learner state
12. current topic loads only relevant mastery domain

## 23. V1 Success Criteria

V1 is successful when:

- the same repository installs into Claude Code and Codex as an Agent Skill
- global context is never read before explicit permission
- denying access still gives a complete learning experience
- a returning learner is not forced through redundant onboarding
- old context does not automatically count as mastery
- the tutor can create and navigate a dependency map
- the tutor requires evidence before mastery promotion
- persistent memory is not rewritten every prompt
- learner state becomes more accurate without unbounded growth
- only relevant mastery data is loaded for a lesson
- shared learner state can be used by both Claude Code and Codex on the same machine
- core merge behavior is deterministic and testable

## 24. Deferred V2 Ideas

- spaced retrieval and revisit scheduling
- forgetting/decay model
- machine-to-machine shared sync
- encrypted learner store
- optional MCP learner service
- semantic retrieval over large session archives
- richer visual teaching adapters
- analytics dashboard for learner progress
- import/export learner profile

