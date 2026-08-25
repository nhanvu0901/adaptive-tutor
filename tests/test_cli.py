import json
import subprocess
import sys
import unittest
from pathlib import Path

from tests.helpers import temp_root
from skills.adaptive_tutor.scripts.learner_store import LearnerStore


SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "adaptive-tutor" / "scripts" / "merge_delta.py"


class CheckpointCliTests(unittest.TestCase):
    def test_checkpoint_writes_only_referenced_mastery_domain(self):
        root = temp_root(self)
        store = LearnerStore(root)
        store.load_learner()
        learner_before = (root / "LEARNER.yaml").read_text(encoding="utf-8")
        delta_path = root / "checkpoint.json"
        delta_path.write_text(json.dumps({"schema_version": 1, "mastery": [{
            "domain": "nlp", "concept": "embeddings", "to": "can_explain",
            "confidence": 0.8, "evidence_type": "explanation", "strength": "strong",
            "max_hint_level": 1,
        }]}), encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--delta", str(delta_path), "--root", str(root)],
            cwd=root, capture_output=True, text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["written"])
        self.assertTrue((root / "mastery" / "nlp.yaml").exists())
        self.assertFalse((root / "mastery" / "cloud.yaml").exists())
        self.assertEqual((root / "LEARNER.yaml").read_text(encoding="utf-8"), learner_before)
