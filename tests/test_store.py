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

    def test_distinct_domain_names_round_trip_without_overwrite(self):
        root = temp_root(self)
        store = LearnerStore(root)
        for domain in ("C", "C++"):
            store.save_mastery(domain, {
                "schema_version": 1,
                "domain": domain,
                "concepts": {"syntax": {"state": "exposed", "confidence": 0.5}},
            })

        self.assertEqual(store.load_mastery("C")["domain"], "C")
        self.assertEqual(store.load_mastery("C++")["domain"], "C++")
        self.assertEqual(len(list((root / "mastery").glob("*.yaml"))), 2)

    def test_simple_lowercase_domain_keeps_legacy_filename(self):
        root = temp_root(self)
        store = LearnerStore(root)
        store.save_mastery("nlp", {"schema_version": 1, "domain": "nlp", "concepts": {}})

        self.assertTrue((root / "mastery" / "nlp.yaml").is_file())

    def test_corrupt_existing_state_is_preserved(self):
        root = temp_root(self)
        root.mkdir(parents=True, exist_ok=True)
        path = root / "LEARNER.yaml"
        path.write_text("not-json", encoding="utf-8")
        store = LearnerStore(root)
        with self.assertRaises(ValueError):
            store.load_learner()
        self.assertEqual(path.read_text(encoding="utf-8"), "not-json")

    def test_archive_session_accepts_an_iso_date(self):
        root = temp_root(self)
        path = LearnerStore(root).archive_session("NLP Basics", "# Notes", "2026-01-01")
        self.assertEqual(path, root / "sessions" / "2026-01-01-nlp-basics.md")
        self.assertEqual(path.read_text(encoding="utf-8"), "# Notes")

    def test_archive_session_rejects_traversal_dates_without_writing(self):
        root = temp_root(self)
        store = LearnerStore(root)
        for archive_date in ("../../x", "2026-01-01/../x"):
            with self.subTest(archive_date=archive_date):
                with self.assertRaises(ValueError):
                    store.archive_session("topic", "# Notes", archive_date)
        self.assertFalse((root / "sessions").exists())
