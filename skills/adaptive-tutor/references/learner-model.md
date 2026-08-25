# Learner Model and Checkpoints

Use three storage tiers:

- **Tier 1 — Learner Profile** (`~/.adaptive-tutor/LEARNER.yaml` by default):
  small, frequently loaded state for goals, stable interests, background,
  language, teaching preferences, durable strengths/weaknesses, constraints, and
  persisted consent decisions.
- **Tier 2 — Mastery Index** (`~/.adaptive-tutor/mastery/<domain>.yaml`): load
  only the relevant domain. Concepts progress through `unknown`, `exposed`,
  `can_explain`, `can_apply`, and `can_transfer`, with confidence, verification
  date, and evidence.
- **Tier 3 — Session Archive** (`~/.adaptive-tutor/sessions/YYYY-MM-DD-topic.md`):
  cold storage for the lesson map, exercises, mistakes, hints, durable evidence,
  and final delta. Do not load it by default.

## Working evidence and semantic checkpoints

Maintain a pending evidence buffer in the active lesson only. It records concept,
evidence type, strength, hint use, and provenance (for example,
`independent_explanation`, `unseen_application`, `learner_response`). It is not
persistent learner memory.

Do not persist after every prompt or on a fixed message count. Create a semantic
checkpoint when a concept node or transfer exercise completes, a meaningful
misconception is corrected, a durable preference is repeated or strongly
evidenced, the lesson ends, or the learner explicitly asks to save. A checkpoint
may produce no persistent change.

At a checkpoint, emit only bounded JSON state changes, never a prose summary or a
rewritten learner file. Its shape follows `assets/delta.schema.json`:

```json
{
  "schema_version": 1,
  "mastery": [{
    "domain": "topic", "concept": "concept", "from": "exposed",
    "to": "can_apply", "confidence": 0.82, "evidence_type": "application",
    "strength": "strong", "max_hint_level": 1, "verified_at": "YYYY-MM-DD"
  }],
  "misconceptions": [{"concept": "concept", "status": "corrected"}],
  "preferences": [{
    "key": "systems_concepts", "value": "visual_first", "confidence": 0.72,
    "evidence_type": "explanation", "strength": "medium", "source": "lesson"
  }],
  "profile": [{"field": "goals", "value": "...", "source": "explicit_user"}]
}
```

Preserve evidence provenance in the type, strength, hint level, verification date,
and session archive. Global context and self-report remain provisional and cannot
be emitted as verified mastery without demonstrated evidence.

Treat inferred teaching preferences as candidates first. Repeated supporting
evidence for the same strategy increases `candidate_preferences`; each new
candidate records its strategy identity so evidence for distinct strategies never
combines. Legacy candidates without a strategy remain valid and gain an identity
when the next unambiguous supporting signal arrives. The deterministic gate
promotes a candidate only after sufficient same-strategy support. A strong explicit
user instruction may be stored as a durable preference immediately.

Create the delta file in a temporary or current-workspace location, then run once
per meaningful checkpoint:

```bash
python <skill-dir>/scripts/merge_delta.py --delta <checkpoint-delta.json>
```

The script validates, gates, and merges deterministically. Delete the temporary
delta after a successful merge; retain it when the command fails for diagnosis or
retry.
