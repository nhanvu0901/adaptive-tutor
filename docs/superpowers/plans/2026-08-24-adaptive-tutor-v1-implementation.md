# Adaptive Tutor Skill V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a terminal-native, cross-agent Adaptive Tutor skill pack for Claude Code and Codex with permission-gated context personalization and a local shared learner model that evolves through evidence-driven checkpoint consolidation rather than per-prompt memory rewrites.

**Architecture:** Ship two self-contained Agent Skills: `adaptive-tutor` for the tutoring/memory workflow and `learn-verify` for source verification. The adaptive tutor stores shared local state under `~/.adaptive-tutor/`, keeps runtime assets inside the skill directory so `npx skills add` can copy/symlink them safely, and uses dependency-free Python scripts for validation, gating, deterministic merge, and storage. The LLM observes lesson evidence and emits small deltas; deterministic code validates, filters, and merges those deltas.

**Tech Stack:** Agent Skills (`SKILL.md` + references/scripts/assets), Python 3.10+ standard library only, JSON Schema documents for contracts, YAML-compatible JSON-subset state files, Markdown session archives, `unittest`, `npx skills` for distribution testing.

**Spec:** `docs/superpowers/specs/2026-08-24-adaptive-tutor-v1-design.md`

## Global Constraints

- V1 is terminal-native; no HTML/web dashboard, server, daemon, MCP memory service, vector database, or cloud database.
- Ask explicit permission before actively reading Claude/Codex global context or memory.
- Permission copy must explain that gathered context is used only for learning personalization.
- Permission values are exactly `allow_once`, `allow_and_remember`, and `deny`.
- `allow_once` must never be persisted; `allow_and_remember` may persist only the permission decision.
- Denial or unavailable global context must fall back to onboarding without degrading the learning workflow.
- Existing context is provisional evidence only; it must never directly mark a concept as verified mastery.
- Persistent learner state lives under `~/.adaptive-tutor/` by default and is shared by Claude Code and Codex on the same machine.
- Persistent memory is updated at semantic checkpoints, never on every prompt and never by fixed message count.
- The LLM emits a bounded state delta; Python validates/gates/merges it deterministically.
- Runtime skill files must be self-contained inside each `skills/<skill-name>/` directory because cross-agent installers may install skill directories independently.
- Python runtime code must use only the Python 3.10+ standard library; no PyYAML/jsonschema dependency is allowed in V1.
- Files named `*.yaml` are serialized as JSON text, which is valid YAML 1.2, so scripts can remain dependency-free and state stays human-readable.
- Session history is cold storage and is not loaded by default.
- MCQ/native pickers are for calibration and recognition; `can_explain`, `can_apply`, and `can_transfer` require stronger evidence.
- Strong explicit learning preferences may persist immediately; inferred preferences use candidate-to-confirmed promotion.
- `learn-verify` behavior may be adapted from the MIT-licensed Alvarmethod repository with attribution in `THIRD_PARTY_NOTICES.md`.
- Current Agent Skills packaging must remain compatible with the open Agent Skills standard used by both Claude Code and Codex.

---

## File Map

### Repository/support files

- `README.md` — user-facing purpose, privacy model, install/use examples for Claude Code and Codex, local-state explanation.
- `LICENSE` — MIT license for this repository.
- `THIRD_PARTY_NOTICES.md` — attribution for Alvarmethod-derived ideas/text and upstream MIT license notice.
- `.gitignore` — Python cache/test artifacts only; learner data is outside the repo by default.
- `docs/superpowers/specs/2026-08-24-adaptive-tutor-v1-design.md` — approved design.
- `docs/superpowers/plans/2026-08-24-adaptive-tutor-v1-implementation.md` — this plan.

### Adaptive Tutor skill

- `skills/adaptive-tutor/SKILL.md` — orchestration contract: permission → context → onboarding/calibration → map → teach/prove → checkpoint → delta/gate/merge.
- `skills/adaptive-tutor/references/privacy.md` — exact permission and retention rules.
- `skills/adaptive-tutor/references/pedagogy.md` — one-node teaching loop, evidence ladder, hint ladder, mastery rules.
- `skills/adaptive-tutor/references/learner-model.md` — storage tiers, delta format, checkpoint rules, candidate preferences.
- `skills/adaptive-tutor/references/host-adapters.md` — Claude/Codex global-context and native-quiz capability discovery, plus graceful fallback.
- `skills/adaptive-tutor/references/verification-fallback.md` — verification behavior when `learn-verify` is unavailable.
- `skills/adaptive-tutor/assets/LEARNER.yaml` — initial learner-profile template using JSON-subset YAML.
- `skills/adaptive-tutor/assets/mastery-domain.yaml` — initial domain template using JSON-subset YAML.
- `skills/adaptive-tutor/assets/learner.schema.json` — documented learner-state contract.
- `skills/adaptive-tutor/assets/mastery.schema.json` — documented mastery contract.
- `skills/adaptive-tutor/assets/delta.schema.json` — documented memory-delta contract.
- `skills/adaptive-tutor/scripts/__init__.py` — makes runtime helpers importable in tests.
- `skills/adaptive-tutor/scripts/model.py` — enums/constants, normalization, evidence/state ranks.
- `skills/adaptive-tutor/scripts/validate_state.py` — dependency-free structural validation for learner, mastery, and delta documents.
- `skills/adaptive-tutor/scripts/learner_store.py` — local root resolution, atomic reads/writes, permission state, relevant-domain state access, session archive helper.
- `skills/adaptive-tutor/scripts/memory_gate.py` — pure deterministic filtering/promotion rules.
- `skills/adaptive-tutor/scripts/merge_delta.py` — pure merge functions plus CLI checkpoint application.

### Verification skill

- `skills/learn-verify/SKILL.md` — falsifiable claim → source lookup → verdict → safe teaching form.
- `skills/learn-verify/references/source-policy.md` — source hierarchy and verdict definitions.

### Tests

- `tests/__init__.py` — test package marker.
- `tests/helpers.py` — temp learner root and fixture loaders.
- `tests/test_model.py` — ranks, evidence normalization, confidence clamp.
- `tests/test_validation.py` — valid/invalid learner/mastery/delta contracts.
- `tests/test_store.py` — missing store creation, permission persistence, atomic corruption protection, domain-only loading.
- `tests/test_gate.py` — mastery promotion, hint dependence, preferences, contradictions, no-op delta.
- `tests/test_merge.py` — deterministic merge and state replacement instead of unbounded append.
- `tests/test_cli.py` — end-to-end checkpoint CLI over a temporary learner root.
- `tests/test_skill_contract.py` — static requirements for permission wording, onboarding fallback, one-node teaching, native quiz fallback, verification integration.
- `tests/test_packaging.py` — runtime self-containment and skill metadata/discovery layout.

---

### Task 1: Repository foundation and portable skill skeleton

**Files:**
- Create: `README.md`
- Create: `LICENSE`
- Create: `THIRD_PARTY_NOTICES.md`
- Create: `.gitignore`
- Create: `skills/adaptive-tutor/SKILL.md`
- Create: `skills/learn-verify/SKILL.md`
- Create: `tests/__init__.py`
- Create: `tests/test_packaging.py`

**Interfaces:**
- Consumes: approved design spec.
- Produces: two discoverable Agent Skills named `adaptive-tutor` and `learn-verify`; repository-level legal/distribution metadata.

- [ ] **Step 1: Initialize Git and create the first failing packaging test**

Run:

```bash
git init
python - <<'PY'
from pathlib import Path
Path('tests').mkdir(exist_ok=True)
Path('tests/__init__.py').write_text('', encoding='utf-8')
PY
```

Create `tests/test_packaging.py`:

```python
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_expected_skills_have_agent_skill_frontmatter(self):
        for name in ("adaptive-tutor", "learn-verify"):
            path = ROOT / "skills" / name / "SKILL.md"
            self.assertTrue(path.is_file(), path)
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"))
            self.assertRegex(text, rf"(?m)^name:\s*{re.escape(name)}\s*$")
            self.assertRegex(text, r"(?m)^description:\s*.+$")

    def test_runtime_references_do_not_escape_skill_directory(self):
        for skill_dir in (ROOT / "skills").glob("*"):
            if not (skill_dir / "SKILL.md").exists():
                continue
            for path in skill_dir.rglob("*.md"):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("../../templates/", text)
                self.assertNotIn("../../schemas/", text)
```

- [ ] **Step 2: Run the packaging test and verify it fails**

Run:

```bash
python -m unittest tests.test_packaging -v
```

Expected: FAIL because `skills/adaptive-tutor/SKILL.md` and `skills/learn-verify/SKILL.md` do not exist.

- [ ] **Step 3: Add minimal skill frontmatter and repository metadata**

Create `skills/adaptive-tutor/SKILL.md`:

```markdown
---
name: adaptive-tutor
description: Personalized evidence-driven tutoring that learns a learner over time. Use when the user asks to learn, study, understand, practice, or be taught a topic. Ask permission before reading global Claude/Codex context; never treat remembered context as proof of mastery.
---

# Adaptive Tutor

Follow the workflow in this skill and its references. V1 is terminal-native.
```

Create `skills/learn-verify/SKILL.md`:

```markdown
---
name: learn-verify
description: Verify a factual claim before it is taught as fact. Use for uncertain, niche, current, contested, or materially important claims inside a learning session.
---

# Learn Verify

Turn the teaching claim into a falsifiable claim, inspect authoritative sources when tools permit, and return one of: confirmed, qualified, contradicted, unknown.
```

Create `.gitignore`:

```gitignore
__pycache__/
*.py[cod]
.coverage
.pytest_cache/
```

Create `LICENSE` with the standard MIT license text and the repository copyright holder/year.

Create `THIRD_PARTY_NOTICES.md` with:

```markdown
# Third-Party Notices

## Alvarmethod

This project adapts ideas and may adapt portions of skill text from:
`vasanthsreeram/Alvarmethod`.

Upstream license: MIT.
Upstream repository: https://github.com/vasanthsreeram/Alvarmethod

Retain the upstream MIT notice for any copied or adapted upstream text.
```

Create a minimal `README.md` containing the project name, one-sentence goal, privacy-first note, and “V1: terminal-native, Claude Code + Codex”.

- [ ] **Step 4: Run packaging test and compile check**

Run:

```bash
python -m unittest tests.test_packaging -v
python -m compileall skills tests
```

Expected: PASS.

- [ ] **Step 5: Commit foundation**

```bash
git add .
git commit -m "chore: initialize adaptive tutor skill pack"
```

---

### Task 2: Define dependency-free learner/mastery/delta contracts

**Files:**
- Create: `skills/adaptive-tutor/scripts/__init__.py`
- Create: `skills/adaptive-tutor/scripts/model.py`
- Create: `skills/adaptive-tutor/scripts/validate_state.py`
- Create: `skills/adaptive-tutor/assets/LEARNER.yaml`
- Create: `skills/adaptive-tutor/assets/mastery-domain.yaml`
- Create: `skills/adaptive-tutor/assets/learner.schema.json`
- Create: `skills/adaptive-tutor/assets/mastery.schema.json`
- Create: `skills/adaptive-tutor/assets/delta.schema.json`
- Create: `tests/test_model.py`
- Create: `tests/test_validation.py`

**Interfaces:**
- Produces: `STATE_RANK`, `EVIDENCE_RANK`, `clamp_confidence(value)`, `validate_learner(data)`, `validate_mastery(data)`, `validate_delta(data)`.
- Storage rule: `*.yaml` files contain JSON syntax so `json.load` can parse them without third-party libraries.

- [ ] **Step 1: Write failing model tests**

Create `tests/test_model.py`:

```python
import unittest
from skills.adaptive_tutor.scripts.model import (
    EVIDENCE_RANK,
    STATE_RANK,
    clamp_confidence,
)


class ModelTests(unittest.TestCase):
    def test_state_order_is_monotonic(self):
        self.assertLess(STATE_RANK["unknown"], STATE_RANK["exposed"])
        self.assertLess(STATE_RANK["exposed"], STATE_RANK["can_explain"])
        self.assertLess(STATE_RANK["can_explain"], STATE_RANK["can_apply"])
        self.assertLess(STATE_RANK["can_apply"], STATE_RANK["can_transfer"])

    def test_transfer_is_stronger_than_self_report(self):
        self.assertGreater(EVIDENCE_RANK["transfer"], EVIDENCE_RANK["self_report"])

    def test_confidence_is_clamped(self):
        self.assertEqual(clamp_confidence(-0.2), 0.0)
        self.assertEqual(clamp_confidence(1.2), 1.0)
        self.assertEqual(clamp_confidence(0.72), 0.72)
```

- [ ] **Step 2: Run model tests and verify failure**

```bash
python -m unittest tests.test_model -v
```

Expected: import failure because `model.py` does not exist.

- [ ] **Step 3: Implement model constants**

Create `skills/adaptive-tutor/scripts/model.py`:

```python
STATE_RANK = {
    "unknown": 0,
    "exposed": 1,
    "can_explain": 2,
    "can_apply": 3,
    "can_transfer": 4,
}

EVIDENCE_RANK = {
    "self_report": 0,
    "recognition": 1,
    "recall": 2,
    "explanation": 3,
    "application": 4,
    "transfer": 5,
    "repeated_success": 6,
    "contradiction": 6,
    "explicit_preference": 6,
}

STRENGTH_RANK = {"weak": 1, "medium": 2, "strong": 3}
PERMISSIONS = {"allow_once", "allow_and_remember", "deny"}


def clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
```

- [ ] **Step 4: Write failing validation tests**

Create `tests/test_validation.py` with fixtures that exercise all three contracts:

```python
import unittest
from skills.adaptive_tutor.scripts.validate_state import (
    ValidationError,
    validate_delta,
    validate_learner,
    validate_mastery,
)


class ValidationTests(unittest.TestCase):
    def test_valid_learner(self):
        validate_learner({
            "schema_version": 1,
            "permissions": {"claude_global": "deny", "codex_global": "deny"},
            "goals": [],
            "interests": [],
            "background": [],
            "preferences": {},
            "candidate_preferences": {},
            "constraints": {},
        })

    def test_allow_once_cannot_be_persisted(self):
        with self.assertRaises(ValidationError):
            validate_learner({
                "schema_version": 1,
                "permissions": {"claude_global": "allow_once"},
                "goals": [], "interests": [], "background": [],
                "preferences": {}, "candidate_preferences": {}, "constraints": {},
            })

    def test_mastery_rejects_unknown_state_name(self):
        with self.assertRaises(ValidationError):
            validate_mastery({
                "schema_version": 1,
                "domain": "nlp",
                "concepts": {"attention": {"state": "expert", "confidence": 0.8}},
            })

    def test_delta_requires_schema_version(self):
        with self.assertRaises(ValidationError):
            validate_delta({"mastery": []})
```

- [ ] **Step 5: Run validation tests and verify failure**

```bash
python -m unittest tests.test_validation -v
```

Expected: import failure because validator does not exist.

- [ ] **Step 6: Implement explicit structural validators**

Create `validate_state.py` with `ValidationError(ValueError)` and strict validators. Required behavior:

```python
from .model import PERMISSIONS, STATE_RANK, clamp_confidence

class ValidationError(ValueError):
    pass


def _require_keys(data, keys, label):
    missing = [key for key in keys if key not in data]
    if missing:
        raise ValidationError(f"{label} missing keys: {', '.join(missing)}")


def validate_learner(data):
    _require_keys(data, ["schema_version", "permissions", "goals", "interests",
                         "background", "preferences", "candidate_preferences", "constraints"], "learner")
    if data["schema_version"] != 1:
        raise ValidationError("unsupported learner schema_version")
    for host, decision in data["permissions"].items():
        if decision == "allow_once":
            raise ValidationError("allow_once is session-only and cannot be persisted")
        if decision not in PERMISSIONS:
            raise ValidationError(f"invalid permission for {host}")
    return data
```

Also implement `validate_mastery` and `validate_delta` so they reject unknown concept states, confidence outside `[0,1]`, unknown evidence types, malformed preference evidence, and non-list mastery/misconception entries.

- [ ] **Step 7: Add templates and JSON Schema documentation**

`assets/LEARNER.yaml` must parse with `json.load` and initialize only durable fields:

```json
{
  "schema_version": 1,
  "permissions": {},
  "goals": [],
  "interests": [],
  "background": [],
  "preferences": {},
  "candidate_preferences": {},
  "constraints": {}
}
```

`assets/mastery-domain.yaml`:

```json
{
  "schema_version": 1,
  "domain": "example",
  "concepts": {}
}
```

Document matching contracts in the three `*.schema.json` files; do not add a runtime JSON Schema dependency.

- [ ] **Step 8: Run tests**

```bash
python -m unittest tests.test_model tests.test_validation -v
python -m compileall skills/adaptive-tutor/scripts
```

Expected: PASS.

- [ ] **Step 9: Commit contracts**

```bash
git add skills/adaptive-tutor tests
 git commit -m "feat: define learner state contracts"
```

---

### Task 3: Implement shared local learner store and permission persistence

**Files:**
- Create: `skills/adaptive-tutor/scripts/learner_store.py`
- Create: `tests/helpers.py`
- Create: `tests/test_store.py`

**Interfaces:**
- Produces: `LearnerStore(root: Path | None = None)`, `load_learner()`, `save_learner(data)`, `get_permission(host)`, `set_permission(host, decision)`, `load_mastery(domain)`, `save_mastery(domain, data)`, `archive_session(topic, markdown, date=None)`.
- Atomic mutation: temp file in same directory then `Path.replace`.
- Default root: `Path.home() / ".adaptive-tutor"`; tests always inject a temporary root.

- [ ] **Step 1: Write failing store tests**

Create `tests/helpers.py`:

```python
import tempfile
from pathlib import Path


def temp_root(testcase):
    tmp = tempfile.TemporaryDirectory()
    testcase.addCleanup(tmp.cleanup)
    return Path(tmp.name)
```

Create `tests/test_store.py` covering:

```python
import json
import unittest
from tests.helpers import temp_root
from skills.adaptive_tutor.scripts.learner_store import LearnerStore


class StoreTests(unittest.TestCase):
    def test_missing_store_is_created_from_defaults(self):
        root = temp_root(self)
        store = LearnerStore(root)
        learner = store.load_learner()
        self.assertEqual(learner["schema_version"], 1)
        self.assertTrue((root / "LEARNER.yaml").exists())

    def test_allow_once_is_not_persisted(self):
        root = temp_root(self)
        store = LearnerStore(root)
        store.set_permission("claude_global", "allow_once")
        self.assertIsNone(store.get_permission("claude_global"))

    def test_allow_and_remember_is_persisted(self):
        root = temp_root(self)
        store = LearnerStore(root)
        store.set_permission("codex_global", "allow_and_remember")
        self.assertEqual(LearnerStore(root).get_permission("codex_global"), "allow_and_remember")

    def test_load_mastery_reads_only_named_domain(self):
        root = temp_root(self)
        store = LearnerStore(root)
        store.save_mastery("nlp", {"schema_version": 1, "domain": "nlp", "concepts": {}})
        store.save_mastery("cloud", {"schema_version": 1, "domain": "cloud", "concepts": {}})
        self.assertEqual(store.load_mastery("nlp")["domain"], "nlp")

    def test_corrupt_existing_state_is_preserved(self):
        root = temp_root(self)
        root.mkdir(parents=True, exist_ok=True)
        path = root / "LEARNER.yaml"
        path.write_text("not-json", encoding="utf-8")
        store = LearnerStore(root)
        with self.assertRaises(ValueError):
            store.load_learner()
        self.assertEqual(path.read_text(encoding="utf-8"), "not-json")
```

- [ ] **Step 2: Run store tests and verify failure**

```bash
python -m unittest tests.test_store -v
```

Expected: import failure.

- [ ] **Step 3: Implement store with atomic writes and safe slugs**

Core implementation requirements:

```python
class LearnerStore:
    def __init__(self, root=None):
        self.root = Path(root) if root else Path.home() / ".adaptive-tutor"

    def _atomic_write_json(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temp.replace(path)
```

`set_permission(..., "allow_once")` must return without writing it. `deny` and `allow_and_remember` may be persisted. `archive_session` must sanitize the topic slug and create `sessions/YYYY-MM-DD-<slug>.md`.

- [ ] **Step 4: Run store tests**

```bash
python -m unittest tests.test_store -v
```

Expected: PASS.

- [ ] **Step 5: Commit store**

```bash
git add skills/adaptive-tutor/scripts/learner_store.py tests
 git commit -m "feat: add shared learner store"
```

---

### Task 4: Implement evidence-driven memory gate

**Files:**
- Create: `skills/adaptive-tutor/scripts/memory_gate.py`
- Create: `tests/test_gate.py`

**Interfaces:**
- Consumes: validated delta documents and current learner/mastery state.
- Produces: `gate_delta(delta, learner, mastery_by_domain) -> dict` containing only durable accepted changes.
- Required helper: `required_evidence_rank(target_state)`.

- [ ] **Step 1: Write failing gate tests for mastery**

Create tests proving these policies:

```python
class GateMasteryTests(unittest.TestCase):
    def test_self_report_cannot_promote_to_can_explain(self): ...
    def test_explanation_can_promote_to_can_explain(self): ...
    def test_application_can_promote_to_can_apply(self): ...
    def test_transfer_can_promote_to_can_transfer(self): ...
    def test_heavy_hint_blocks_can_transfer_promotion(self): ...
    def test_recent_strong_contradiction_can_reduce_confidence(self): ...
```

Use target evidence thresholds:

```python
REQUIRED_EVIDENCE = {
    "unknown": "self_report",
    "exposed": "recognition",
    "can_explain": "explanation",
    "can_apply": "application",
    "can_transfer": "transfer",
}
```

Hint policy:

- `can_explain`: maximum hint level 3.
- `can_apply`: maximum hint level 2.
- `can_transfer`: maximum hint level 1.

- [ ] **Step 2: Run mastery gate tests and verify failure**

```bash
python -m unittest tests.test_gate.GateMasteryTests -v
```

Expected: FAIL because gate does not exist.

- [ ] **Step 3: Implement mastery filtering**

Implement pure functions using `STATE_RANK`, `EVIDENCE_RANK`, and the target-state thresholds. A rejected promotion must disappear from the returned delta; it must not be silently downgraded to a different promotion.

Contradiction behavior: a delta entry with `evidence_type="contradiction"`, `strength="strong"`, and confidence lower than current may reduce confidence. If the delta explicitly includes a lower state, accept the lower state only when contradiction evidence is strong and `verified_at` is present.

- [ ] **Step 4: Write failing preference/profile gate tests**

Add tests:

```python
class GatePreferenceTests(unittest.TestCase):
    def test_one_inferred_preference_signal_stays_candidate(self): ...
    def test_third_supporting_signal_promotes_candidate(self): ...
    def test_explicit_preference_promotes_immediately(self): ...
    def test_goal_change_requires_explicit_user_evidence(self): ...
    def test_empty_delta_returns_no_changes(self): ...
```

Candidate promotion threshold for V1: `evidence_count >= 3` and `confidence >= 0.70`.

- [ ] **Step 5: Implement preference/profile gating**

Accepted inferred preference signals increment candidate state; they do not directly update `preferences`. Explicit preference entries with `evidence_type="explicit_preference"` may update `preferences` immediately. Goal/interest/background/constraint mutation requires `source="explicit_user"`.

- [ ] **Step 6: Run all gate tests**

```bash
python -m unittest tests.test_gate -v
```

Expected: PASS.

- [ ] **Step 7: Commit gate**

```bash
git add skills/adaptive-tutor/scripts/memory_gate.py tests/test_gate.py
 git commit -m "feat: gate learner memory by evidence"
```

---

### Task 5: Implement deterministic delta merge and checkpoint CLI

**Files:**
- Create: `skills/adaptive-tutor/scripts/merge_delta.py`
- Create: `tests/test_merge.py`
- Create: `tests/test_cli.py`

**Interfaces:**
- Produces: `merge_learner(learner, accepted_delta)`, `merge_mastery(current, accepted_entries)`, `apply_checkpoint(store, delta) -> dict`, CLI `python merge_delta.py --delta FILE [--root DIR]`.
- CLI output: compact JSON summary listing updated profile fields, mastery concepts, misconceptions, and whether anything was written.

- [ ] **Step 1: Write failing merge tests**

Required cases:

```python
class MergeTests(unittest.TestCase):
    def test_mastery_replaces_concept_state_instead_of_appending_history(self): ...
    def test_preference_candidate_count_merges_deterministically(self): ...
    def test_confirmed_preference_removes_candidate(self): ...
    def test_same_input_state_and_delta_produce_same_output(self): ...
    def test_noop_delta_does_not_change_state(self): ...
```

- [ ] **Step 2: Run merge tests and verify failure**

```bash
python -m unittest tests.test_merge -v
```

Expected: FAIL because merge module does not exist.

- [ ] **Step 3: Implement pure merge functions**

Use copy-on-write (`copy.deepcopy`) so input state is never mutated. Mastery concept records keep only current durable state plus bounded evidence metadata:

```json
{
  "state": "can_apply",
  "confidence": 0.82,
  "last_verified": "2026-08-24",
  "evidence": {"strongest_type": "application", "count": 3, "max_hint_level": 1}
}
```

Do not append full question/answer history to mastery files.

- [ ] **Step 4: Write failing CLI test**

The test must create a temporary learner root, write a delta file, execute the script with `subprocess.run`, and assert:

- exit code `0`
- JSON stdout has `"written": true`
- only the referenced mastery domain file is created
- `LEARNER.yaml` is unchanged when there is no profile delta

- [ ] **Step 5: Implement `apply_checkpoint` and CLI**

CLI arguments:

```text
--delta PATH     required
--root PATH      optional test/custom store root
--dry-run        validate/gate/merge but write nothing
```

Workflow:

```text
load delta -> validate -> load only referenced mastery domains -> gate -> pure merge -> validate outputs -> atomic writes -> print summary
```

On malformed/corrupt state: non-zero exit, error on stderr, no overwrite of existing state.

- [ ] **Step 6: Run merge and CLI tests**

```bash
python -m unittest tests.test_merge tests.test_cli -v
```

Expected: PASS.

- [ ] **Step 7: Commit checkpoint engine**

```bash
git add skills/adaptive-tutor/scripts/merge_delta.py tests
 git commit -m "feat: add deterministic memory consolidation"
```

---

### Task 6: Author privacy, learner-model, and pedagogy runtime references

**Files:**
- Create: `skills/adaptive-tutor/references/privacy.md`
- Create: `skills/adaptive-tutor/references/learner-model.md`
- Create: `skills/adaptive-tutor/references/pedagogy.md`
- Create: `tests/test_skill_contract.py`

**Interfaces:**
- Consumes: memory scripts from Tasks 2–5.
- Produces: exact instructions the host LLM follows; static contract tests prevent permission/pedagogy regressions.

- [ ] **Step 1: Write failing skill contract tests**

Create `tests/test_skill_contract.py`:

```python
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "skills/adaptive-tutor/SKILL.md").read_text(encoding="utf-8")


class SkillContractTests(unittest.TestCase):
    def test_permission_precedes_global_context_read(self):
        self.assertIn("before reading any global", SKILL.lower())
        self.assertIn("only for learning personalization", SKILL.lower())

    def test_denial_has_onboarding_fallback(self):
        self.assertIn("five-question onboarding", SKILL.lower())

    def test_context_never_counts_as_mastery(self):
        self.assertIn("not proof of mastery", SKILL.lower())

    def test_memory_is_checkpointed_not_per_prompt(self):
        self.assertIn("semantic checkpoint", SKILL.lower())
        self.assertIn("do not persist after every prompt", SKILL.lower())

    def test_teaching_is_one_node_at_a_time(self):
        self.assertIn("one unresolved node", SKILL.lower())
```

- [ ] **Step 2: Run contract tests and verify failure**

```bash
python -m unittest tests.test_skill_contract -v
```

Expected: FAIL because current `SKILL.md` is only a stub.

- [ ] **Step 3: Write `privacy.md` with exact permission state machine**

Include the exact user-facing permission request:

```text
I can use your existing Claude/Codex global context to understand your background, interests, and prior knowledge so I can personalize how I teach you. I will use this information only for learning personalization. May I read it?
```

Then define:

```text
allow_once          -> read for this learning session; do not persist permission
allow_and_remember  -> read; persist only permission decision
 deny                -> do not read; start/continue with onboarding + shared learner state
```

Also state: do not copy global files into learner storage; extract only learning-relevant signals; discard unrelated/sensitive data; current project/conversation context already provided by the host is not an authorization to actively open global files.

- [ ] **Step 4: Write `learner-model.md`**

Document Tier 1/Tier 2/Tier 3, pending evidence buffer, semantic checkpoint triggers, delta JSON shape, evidence provenance, candidate preferences, and the command pattern:

```bash
python <skill-dir>/scripts/merge_delta.py --delta <checkpoint-delta.json>
```

Instruct the tutor to create the delta file in a temporary/current-workspace location, run merge once per meaningful checkpoint, then delete the temporary delta after successful merge.

- [ ] **Step 5: Write `pedagogy.md`**

Encode:

```text
CONTEXT -> CALIBRATE -> MAP -> TEACH -> PROVE -> DELTA -> GATE -> MERGE -> REVISIT
```

Calibration modes:

- context-rich: 1–3 high-information questions
- context-poor: five-question onboarding as needed, then 5–10 adaptive probe questions, stopping early when boundary is clear

Teaching node loop:

```text
connect -> minimal explanation -> retrieval/explanation -> application -> transfer when appropriate -> evidence -> checkpoint
```

Hint ladder levels 1–6 exactly as in the spec and note that hint dependence weakens evidence.

- [ ] **Step 6: Expand `SKILL.md` to orchestrate references**

Keep the top-level skill concise. It must explicitly load the three references when needed, state the permission hard gate in the main body, include the five onboarding questions, and give host-neutral commands for the checkpoint script.

- [ ] **Step 7: Run contract and packaging tests**

```bash
python -m unittest tests.test_skill_contract tests.test_packaging -v
```

Expected: PASS.

- [ ] **Step 8: Commit runtime instructions**

```bash
git add skills/adaptive-tutor tests/test_skill_contract.py
 git commit -m "feat: add adaptive tutoring workflow"
```

---

### Task 7: Add Claude/Codex native interaction adapters and verification integration

**Files:**
- Create: `skills/adaptive-tutor/references/host-adapters.md`
- Create: `skills/adaptive-tutor/references/verification-fallback.md`
- Create: `skills/learn-verify/references/source-policy.md`
- Modify: `skills/learn-verify/SKILL.md`
- Modify: `skills/adaptive-tutor/SKILL.md`
- Modify: `THIRD_PARTY_NOTICES.md`
- Modify: `tests/test_skill_contract.py`

**Interfaces:**
- Produces: host capability selection rules for permission prompt/quiz rendering; `learn-verify` verdict contract `confirmed|qualified|contradicted|unknown`.
- Does not hard-require any one tool name; known host-native tools are preferred when present, otherwise plain text fallback.

- [ ] **Step 1: Add failing host/verify contract tests**

Add assertions that runtime instructions contain:

```text
AskUserQuestion
ask_user_question
plain-text fallback
confirmed
qualified
contradicted
unknown
```

Also assert the adaptive tutor says MCQ cannot by itself promote to `can_explain`, `can_apply`, or `can_transfer`.

- [ ] **Step 2: Run tests and verify failure**

```bash
python -m unittest tests.test_skill_contract -v
```

Expected: FAIL on missing adapter/verify requirements.

- [ ] **Step 3: Author `host-adapters.md`**

Rules:

1. Detect the current host from available capabilities/instructions; do not infer solely from filesystem path.
2. For permission and MCQ prompts, prefer a native picker when one is available.
3. Known mappings:
   - Claude Code: prefer `AskUserQuestion` when available.
   - Codex: prefer `ask_user_question` when available.
4. If the named native tool is absent, use the host's equivalent single-choice interaction tool if exposed.
5. If no picker exists, render numbered/plain-text choices and continue; never fail the lesson.
6. Native quiz semantics stay shared: stem, options, correct answer, feedback, evidence type/weight.

Global-context discovery rules must remain capability-based and permission-gated; the adapter may read known global sources only after consent and only when the current environment can access them.

- [ ] **Step 4: Adapt `learn-verify` under MIT terms**

Before copying/adapting upstream text, record the exact upstream revision used:

```bash
git ls-remote https://github.com/vasanthsreeram/Alvarmethod.git refs/heads/main
```

Add the returned commit SHA and retrieval date to `THIRD_PARTY_NOTICES.md`.

The adapted skill must implement:

```text
claim -> make falsifiable -> authoritative/primary source search -> compare evidence -> verdict -> safe teaching form
```

Verdicts:

- `confirmed` — evidence directly supports the claim.
- `qualified` — core claim holds only with material conditions/caveats.
- `contradicted` — good evidence conflicts with the claim.
- `unknown` — insufficient trustworthy evidence; do not teach as fact.

Do not copy unrelated Alvarmethod teaching/profile behavior into this skill.

- [ ] **Step 5: Add verification fallback**

`verification-fallback.md` contains the same verdict semantics at shorter length so the adaptive tutor can verify inline when the separate `learn-verify` skill is not installed/available.

`adaptive-tutor/SKILL.md` must say: invoke `learn-verify` when available for uncertain/current/niche/material claims; otherwise follow verification fallback.

- [ ] **Step 6: Run contract tests**

```bash
python -m unittest tests.test_skill_contract tests.test_packaging -v
```

Expected: PASS.

- [ ] **Step 7: Commit adapters and verification**

```bash
git add skills THIRD_PARTY_NOTICES.md tests/test_skill_contract.py
 git commit -m "feat: add native quiz and verification adapters"
```

---

### Task 8: Add scenario tests for the full V1 memory behavior

**Files:**
- Create: `tests/test_scenarios.py`

**Interfaces:**
- Consumes: `LearnerStore`, `gate_delta`, `apply_checkpoint`.
- Produces: regression coverage for the 12 scenarios from the design spec.

- [ ] **Step 1: Write scenario tests 1–6**

Implement these concrete scenarios using temp roots and JSON delta fixtures:

1. first-time learner denial persists `deny` but no global context data
2. first-time learner allow-and-remember persists only permission
3. returning learner with transfer evidence retains `can_transfer`
4. provisional global-context signal does not promote mastery
5. explicit preference replaces prior preference immediately
6. one inferred preference signal remains candidate only

For scenario 4, the test delta must use `evidence_type="self_report"` or another weak/inferred type and target `can_apply`; gate must reject it.

- [ ] **Step 2: Run scenarios 1–6**

```bash
python -m unittest tests.test_scenarios -v
```

Expected: PASS after test construction; any failure is a real implementation bug and must be fixed before adding more scenarios.

- [ ] **Step 3: Add scenarios 7–12**

7. third repeated preference signal promotes durable preference
8. empty/no-meaningful delta writes nothing
9. unseen transfer success promotes `can_transfer`
10. transfer answer with hint level 5 does not promote `can_transfer`
11. two store instances (representing Claude and Codex) see the same root state
12. loading `nlp` does not parse/read unrelated `cloud` mastery content; make `cloud.yaml` deliberately malformed and prove `load_mastery("nlp")` still succeeds

- [ ] **Step 4: Run full scenario suite**

```bash
python -m unittest tests.test_scenarios -v
```

Expected: PASS.

- [ ] **Step 5: Run full unit suite**

```bash
python -m unittest discover -s tests -v
```

Expected: PASS with all tests green.

- [ ] **Step 6: Commit scenario coverage**

```bash
git add tests/test_scenarios.py
 git commit -m "test: cover adaptive tutor v1 scenarios"
```

---

### Task 9: Complete README, installation verification, and release-ready checks

**Files:**
- Modify: `README.md`
- Modify: `skills/adaptive-tutor/SKILL.md` if install testing exposes path assumptions
- Modify: `skills/learn-verify/SKILL.md` if install testing exposes path assumptions
- Modify: `tests/test_packaging.py`

**Interfaces:**
- Produces: user-installable GitHub-ready repository and documented local-state/privacy behavior.

- [ ] **Step 1: Expand README with the final V1 usage contract**

README sections must include:

```text
What it is
Why it differs from a normal AI tutor
Privacy and permission
How memory stays cost-effective
Install with npx skills
Claude Code usage
Codex usage
Shared local learner state
What V1 does not do
Development/tests
Third-party attribution
```

Installation examples:

```bash
npx skills add <owner>/<repo> -g --all
npx skills add <owner>/<repo> --list
```

Explain that the common CLI installs Agent Skills into agent-specific locations; do not instruct users to manually copy the learner store into either agent directory.

- [ ] **Step 2: Add packaging regression checks for self-contained runtime files**

Extend `test_packaging.py` so every relative file named by `adaptive-tutor/SKILL.md` exists under `skills/adaptive-tutor/`, and the main runtime script can run from an arbitrary current working directory:

```bash
python /absolute/path/to/skills/adaptive-tutor/scripts/merge_delta.py --help
```

- [ ] **Step 3: Run repository verification**

```bash
python -m unittest discover -s tests -v
python -m compileall skills tests
python skills/adaptive-tutor/scripts/merge_delta.py --help
```

Expected: all tests PASS, compileall succeeds, CLI help exits `0`.

- [ ] **Step 4: Verify Agent Skills discovery with the skills CLI**

From the repository root:

```bash
npx skills add . --list
```

Expected: output lists both `adaptive-tutor` and `learn-verify`.

If the CLI does not support local-path listing in the installed version, use its documented local-repo equivalent; record the exact verified command in README rather than guessing.

- [ ] **Step 5: Test install into isolated fake HOME when supported**

Create a temporary home and run the least-invasive documented `npx skills` install/dry-run/list command available. Verify that installed skill copies contain their `references/`, `scripts/`, and `assets/` directories. Do not overwrite the developer's real Claude/Codex configuration during tests.

- [ ] **Step 6: Perform privacy grep**

Run:

```bash
grep -RniE "global context|global memory|CLAUDE\.md|AGENTS\.md" skills/adaptive-tutor
```

Manually verify every active-read instruction is downstream of the permission hard gate. Fix any ambiguous instruction before release.

- [ ] **Step 7: Run final test suite again**

```bash
python -m unittest discover -s tests -v
python -m compileall skills tests
```

Expected: PASS.

- [ ] **Step 8: Commit release-ready V1**

```bash
git add README.md skills tests THIRD_PARTY_NOTICES.md
git commit -m "docs: prepare adaptive tutor v1 release"
```

---

## Plan Self-Review Results

### Spec coverage

- Permission/context privacy: Tasks 3, 6, 7, 9.
- Five-question fallback and calibration: Task 6.
- Shared three-tier learner model: Tasks 2, 3, 6.
- Evidence buffer/checkpoints/delta-gate-merge: Tasks 4, 5, 6.
- Mastery evidence, contradictions, hint dependence: Tasks 4 and 8.
- Preference candidate promotion: Tasks 4, 5, 8.
- Learning map, one-node teaching, proof loop: Task 6.
- Native quiz adapter: Task 7.
- Learn-verify: Task 7.
- Cross-agent packaging: Tasks 1, 7, 9.
- Corrupt-state protection and domain-only loading: Tasks 3, 5, 8.
- All 12 scenario tests: Task 8.
- Terminal-native/no web UI: Global Constraints + Task 6.

### Placeholder scan

No implementation step contains placeholder markers, vague cross-task references, or unspecified testing/error-handling work. Where code is not reproduced in full, the exact interface, cases, constraints, and expected command behavior are specified.

### Type/interface consistency

- `LearnerStore` is defined in Task 3 and consumed by Tasks 5/8.
- `validate_*` contracts are defined in Task 2 and consumed by Tasks 3–5.
- `gate_delta` is defined in Task 4 and consumed by Task 5/8.
- `apply_checkpoint` is defined in Task 5 and consumed by Task 8.
- Persistent permission rules use the same three canonical values everywhere; `allow_once` is accepted as a session choice but explicitly rejected from persistent learner files.

