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
