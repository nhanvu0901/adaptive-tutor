import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "skills/adaptive-tutor/SKILL.md").read_text(encoding="utf-8")
PRIVACY = (ROOT / "skills/adaptive-tutor/references/privacy.md").read_text(encoding="utf-8")
LEARNER_MODEL = (ROOT / "skills/adaptive-tutor/references/learner-model.md").read_text(
    encoding="utf-8"
)
PEDAGOGY = (ROOT / "skills/adaptive-tutor/references/pedagogy.md").read_text(encoding="utf-8")


def permission_gate_section(skill):
    """Return only the permission hard-gate section, excluding later headings."""
    heading = "## permission and context hard gate"
    normalized_skill = skill.lower()
    start = normalized_skill.index(heading)
    next_heading = normalized_skill.find("\n## ", start + len(heading))
    if next_heading == -1:
        next_heading = len(skill)
    return " ".join(normalized_skill[start:next_heading].split())


class SkillContractTests(unittest.TestCase):
    def test_permission_gate_precedes_active_global_context_read(self):
        gate = permission_gate_section(SKILL)
        ask_index = gate.index("ask the exact permission request")
        no_read_index = gate.index("do not actively open global files")
        self.assertLess(ask_index, no_read_index)
        self.assertIn("before reading any global claude/codex context or memory", gate)
        self.assertIn("only for learning personalization", gate)

    def test_permission_gate_does_not_use_later_section_text(self):
        fixture = """## Permission and context hard gate
Before reading any global Claude/Codex context or memory, ask the exact permission request.
Use it only for learning personalization.

## Later section
Do not actively open global files until consent is granted.
"""
        gate = permission_gate_section(fixture)
        self.assertNotIn("do not actively open global files", gate)
        with self.assertRaises(ValueError):
            gate.index("do not actively open global files")

    def test_denial_has_onboarding_fallback(self):
        self.assertIn("five-question onboarding", SKILL.lower())

    def test_context_never_counts_as_mastery(self):
        self.assertIn("not proof of mastery", SKILL.lower())

    def test_memory_is_checkpointed_not_per_prompt(self):
        self.assertIn("semantic checkpoint", SKILL.lower())
        self.assertIn("do not persist after every prompt", SKILL.lower())

    def test_teaching_is_one_node_at_a_time(self):
        self.assertIn("one unresolved node", SKILL.lower())

    def test_privacy_reference_has_exact_permission_request(self):
        self.assertIn(
            "I can use your existing Claude/Codex global context to understand your "
            "background, interests, and prior knowledge so I can personalize how I teach "
            "you. I will use this information only for learning personalization. May I read it?",
            PRIVACY,
        )

    def test_privacy_reference_has_all_permission_transitions(self):
        for transition in (
            "allow_once          -> read for this learning session; do not persist permission",
            "allow_and_remember  -> read; persist only permission decision",
            "deny                -> do not read; start/continue with onboarding + shared learner state",
        ):
            self.assertIn(transition, PRIVACY)

    def test_privacy_reference_prevents_global_context_copying(self):
        privacy = " ".join(PRIVACY.lower().split())
        self.assertIn("do not copy global files into learner storage.", privacy)
        self.assertIn("extract only learning-relevant signals", privacy)
        self.assertIn("discard unrelated or sensitive data.", privacy)

    def test_skill_has_exact_five_question_onboarding(self):
        for question in (
            "What do you want to be able to do after learning this topic?",
            "What have you already studied, built, or used that is related to it?",
            "What level do you think you are at, and what is one example that supports that estimate?",
            "What subjects, projects, or interests should I use for examples when helpful?",
            "How do you prefer to learn: pace, language, intuition vs. math, code vs. theory, and amount of practice?",
        ):
            self.assertIn(question, SKILL)

    def test_learner_model_reference_has_tiers_and_checkpoint_rules(self):
        for tier in ("Tier 1 — Learner Profile", "Tier 2 — Mastery Index", "Tier 3 — Session Archive"):
            self.assertIn(tier, LEARNER_MODEL)
        self.assertIn("pending evidence buffer", LEARNER_MODEL)
        self.assertIn("semantic checkpoint", LEARNER_MODEL.lower())
        self.assertIn("Do not persist after every prompt", LEARNER_MODEL)

    def test_pedagogy_reference_has_full_evidence_loop(self):
        self.assertIn(
            "CONTEXT -> CALIBRATE -> MAP -> TEACH -> PROVE -> DELTA -> GATE -> MERGE -> REVISIT",
            PEDAGOGY,
        )
        self.assertIn(
            "connect -> minimal explanation -> retrieval/explanation -> application -> "
            "transfer when appropriate -> evidence -> checkpoint",
            PEDAGOGY,
        )

    def test_pedagogy_reference_has_six_hint_levels(self):
        for level in (
            "1. restate the goal/question",
            "2. small cue",
            "3. targeted hint",
            "4. partial scaffold",
            "5. worked sub-example",
            "6. full explanation",
        ):
            self.assertIn(level, PEDAGOGY)
        self.assertIn("Hint dependence weakens evidence", PEDAGOGY)

    def test_runtime_instructions_cover_native_interaction_and_verification(self):
        """Catch removal of picker fallbacks or verification verdicts from the runtime."""
        runtime_instructions = "\n".join((SKILL, PEDAGOGY))
        for requirement in (
            "AskUserQuestion",
            "ask_user_question",
            "plain-text fallback",
            "confirmed",
            "qualified",
            "contradicted",
            "unknown",
        ):
            self.assertIn(requirement, runtime_instructions)

    def test_mcq_alone_cannot_promote_higher_mastery_tiers(self):
        """Catch treating recognition evidence as sufficient for higher-order mastery."""
        for tier in ("can_explain", "can_apply", "can_transfer"):
            self.assertIn(f"MCQ cannot by itself promote to `{tier}`", SKILL)
