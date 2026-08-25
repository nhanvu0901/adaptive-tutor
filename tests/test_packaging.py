import re
import subprocess
import sys
import tempfile
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

    def test_adaptive_tutor_runtime_files_are_self_contained(self):
        skill_dir = ROOT / "skills" / "adaptive-tutor"
        skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        runtime_paths = re.findall(
            r"`((?:references|scripts|assets)/[^`\s>]+)`", skill_text
        )
        self.assertTrue(runtime_paths, "SKILL.md should name its runtime files")
        for relative_path in runtime_paths:
            path = skill_dir / relative_path
            self.assertTrue(path.is_file(), path)

    def test_merge_delta_help_runs_from_an_arbitrary_working_directory(self):
        script = ROOT / "skills" / "adaptive-tutor" / "scripts" / "merge_delta.py"
        with tempfile.TemporaryDirectory() as working_directory:
            result = subprocess.run(
                [sys.executable, str(script), "--help"],
                cwd=working_directory,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout)
