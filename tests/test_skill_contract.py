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
