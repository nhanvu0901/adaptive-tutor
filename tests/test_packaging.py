import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_plugin_manifests_expose_the_portable_skills(self):
        manifest_paths = (
            ROOT / ".codex-plugin" / "plugin.json",
            ROOT / ".claude-plugin" / "plugin.json",
        )
        for path in manifest_paths:
            self.assertTrue(path.is_file(), path)
            manifest = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["name"], "adaptive-tutor")
            self.assertEqual(manifest["version"], "1.0.0")
            self.assertEqual(manifest["skills"], "./skills")
            self.assertEqual(manifest["repository"], "https://github.com/nhanvu0901/adaptive-tutor")
            self.assertEqual(manifest["license"], "MIT")
            self.assertTrue(manifest["description"])

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
        skill_root = skill_dir.resolve()
        for relative_path in runtime_paths:
            path = (skill_dir / relative_path).resolve()
            self.assertTrue(path.is_relative_to(skill_root), path)
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

    def test_copied_merge_delta_help_is_self_contained(self):
        source_skill = ROOT / "skills" / "adaptive-tutor"
        with tempfile.TemporaryDirectory() as temporary_directory:
            isolated_root = Path(temporary_directory)
            copied_skill = isolated_root / "installed" / "adaptive-tutor"
            shutil.copytree(source_skill, copied_skill)
            working_directory = isolated_root / "elsewhere"
            working_directory.mkdir()
            result = subprocess.run(
                [sys.executable, "-B", str(copied_skill / "scripts" / "merge_delta.py"), "--help"],
                cwd=working_directory,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout)
