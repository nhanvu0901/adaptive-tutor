"""End-to-end V1 learner-memory scenarios using durable local state."""

import json
import unittest

from skills.adaptive_tutor.scripts.learner_store import LearnerStore
from skills.adaptive_tutor.scripts.memory_gate import gate_delta
from skills.adaptive_tutor.scripts.merge_delta import apply_checkpoint
from tests.helpers import temp_root


def delta(source):
    """Return a hand-authored JSON checkpoint fixture."""
    return json.loads(source)


class V1MemoryScenarioTests(unittest.TestCase):
    def test_first_time_denial_persists_only_deny_without_global_context_data(self):
        root = temp_root(self)
        store = LearnerStore(root)

        store.set_permission("claude_global", "deny")

        learner = LearnerStore(root).load_learner()
        self.assertEqual(learner["permissions"], {"claude_global": "deny"})
        self.assertEqual(learner["goals"], [])
        self.assertEqual(learner["interests"], [])
        self.assertEqual(learner["background"], [])
        self.assertEqual(learner["preferences"], {})
        self.assertEqual(learner["candidate_preferences"], {})
        self.assertEqual(learner["constraints"], {})

    def test_first_time_allow_and_remember_persists_only_permission(self):
        root = temp_root(self)
        store = LearnerStore(root)

        store.set_permission("codex_global", "allow_and_remember")

        learner = LearnerStore(root).load_learner()
        self.assertEqual(learner["permissions"], {"codex_global": "allow_and_remember"})
        self.assertEqual(learner["goals"], [])
        self.assertEqual(learner["interests"], [])
        self.assertEqual(learner["background"], [])
        self.assertEqual(learner["preferences"], {})
        self.assertEqual(learner["candidate_preferences"], {})
        self.assertEqual(learner["constraints"], {})

    def test_returning_learner_with_transfer_evidence_retains_can_transfer(self):
        root = temp_root(self)
        store = LearnerStore(root)
        initial_transfer = delta("""
        {"schema_version": 1, "mastery": [{
          "domain": "nlp", "concept": "embeddings", "to": "can_transfer",
          "confidence": 0.91, "evidence_type": "transfer", "strength": "strong",
          "max_hint_level": 1
        }]}
        """)
        later_checkpoint = delta("""
        {"schema_version": 1, "mastery": [{
          "domain": "nlp", "concept": "attention", "to": "can_apply",
          "confidence": 0.82, "evidence_type": "application", "strength": "strong",
          "max_hint_level": 1
        }]}
        """)

        apply_checkpoint(store, initial_transfer)
        returning_store = LearnerStore(root)
        self.assertEqual(returning_store.load_mastery("nlp")["concepts"]["embeddings"]["state"],
                         "can_transfer")

        summary = apply_checkpoint(returning_store, later_checkpoint)

        self.assertTrue(summary["written"])
        self.assertEqual(returning_store.load_mastery("nlp")["concepts"]["embeddings"]["state"],
                         "can_transfer")

    def test_provisional_global_context_signal_cannot_promote_can_apply(self):
        root = temp_root(self)
        store = LearnerStore(root)
        checkpoint = delta("""
        {"schema_version": 1, "mastery": [{
          "domain": "nlp", "concept": "attention", "to": "can_apply",
          "confidence": 0.95, "evidence_type": "self_report", "strength": "weak",
          "max_hint_level": 0
        }]}
        """)

        accepted = gate_delta(checkpoint, store.load_learner(), {"nlp": store.load_mastery("nlp")})
        summary = apply_checkpoint(store, checkpoint)

        self.assertNotIn("mastery", accepted)
        self.assertFalse(summary["written"])
        self.assertEqual(store.load_mastery("nlp")["concepts"], {})

    def test_explicit_preference_replaces_prior_preference_immediately(self):
        root = temp_root(self)
        store = LearnerStore(root)
        initial = delta("""
        {"schema_version": 1, "preferences": [{
          "key": "systems_concepts", "value": "visual_first", "confidence": 0.80,
          "evidence_type": "explicit_preference", "strength": "strong"
        }]}
        """)
        replacement = delta("""
        {"schema_version": 1, "preferences": [{
          "key": "systems_concepts", "value": "worked_examples", "confidence": 0.92,
          "evidence_type": "explicit_preference", "strength": "strong"
        }]}
        """)
        apply_checkpoint(store, initial)
        self.assertEqual(store.load_learner()["preferences"], {
            "systems_concepts": {"strategy": "visual_first", "confidence": 0.80}
        })

        apply_checkpoint(store, replacement)

        self.assertEqual(LearnerStore(root).load_learner()["preferences"], {
            "systems_concepts": {"strategy": "worked_examples", "confidence": 0.92}
        })

    def test_one_inferred_preference_signal_stays_candidate_only(self):
        root = temp_root(self)
        store = LearnerStore(root)
        checkpoint = delta("""
        {"schema_version": 1, "preferences": [{
          "key": "systems_concepts", "value": "visual_first", "confidence": 0.65,
          "evidence_type": "recognition", "strength": "medium"
        }]}
        """)

        apply_checkpoint(store, checkpoint)

        learner = LearnerStore(root).load_learner()
        self.assertEqual(learner["candidate_preferences"], {
            "systems_concepts": {
                "strategy": "visual_first", "evidence_count": 1, "confidence": 0.65,
            }
        })
        self.assertEqual(learner["preferences"], {})

    def test_third_repeated_preference_signal_promotes_durable_preference(self):
        root = temp_root(self)
        store = LearnerStore(root)
        first_two = delta("""
        {"schema_version": 1, "preferences": [{
          "key": "systems_concepts", "value": "visual_first", "confidence": 0.70,
          "evidence_type": "recognition", "strength": "medium"
        }]}
        """)
        third = delta("""
        {"schema_version": 1, "preferences": [{
          "key": "systems_concepts", "value": "visual_first", "confidence": 0.75,
          "evidence_type": "recognition", "strength": "medium"
        }]}
        """)
        apply_checkpoint(store, first_two)
        apply_checkpoint(store, first_two)

        apply_checkpoint(store, third)

        learner = LearnerStore(root).load_learner()
        self.assertEqual(learner["preferences"], {
            "systems_concepts": {"strategy": "visual_first", "confidence": 0.75}
        })
        self.assertEqual(learner["candidate_preferences"], {})

    def test_empty_no_meaningful_delta_writes_nothing(self):
        root = temp_root(self)
        store = LearnerStore(root)

        summary = apply_checkpoint(store, delta('{"schema_version": 1}'))

        self.assertFalse(summary["written"])
        self.assertFalse((root / "LEARNER.yaml").exists())
        self.assertFalse((root / "mastery").exists())

    def test_unseen_transfer_success_promotes_can_transfer(self):
        root = temp_root(self)
        store = LearnerStore(root)
        checkpoint = delta("""
        {"schema_version": 1, "mastery": [{
          "domain": "nlp", "concept": "attention", "to": "can_transfer",
          "confidence": 0.88, "evidence_type": "transfer", "strength": "strong",
          "max_hint_level": 1
        }]}
        """)

        apply_checkpoint(store, checkpoint)

        self.assertEqual(store.load_mastery("nlp")["concepts"]["attention"]["state"],
                         "can_transfer")

    def test_transfer_answer_with_hint_level_five_does_not_promote_can_transfer(self):
        root = temp_root(self)
        store = LearnerStore(root)
        checkpoint = delta("""
        {"schema_version": 1, "mastery": [{
          "domain": "nlp", "concept": "attention", "to": "can_transfer",
          "confidence": 0.99, "evidence_type": "transfer", "strength": "strong",
          "max_hint_level": 5
        }]}
        """)

        summary = apply_checkpoint(store, checkpoint)

        self.assertFalse(summary["written"])
        self.assertEqual(store.load_mastery("nlp")["concepts"], {})

    def test_two_store_instances_share_the_same_root_state(self):
        root = temp_root(self)
        claude_store = LearnerStore(root)
        codex_store = LearnerStore(root)
        checkpoint = delta("""
        {"schema_version": 1, "profile": [{
          "field": "goals", "value": "understand attention",
          "source": "explicit_user"
        }]}
        """)

        apply_checkpoint(claude_store, checkpoint)

        self.assertEqual(codex_store.load_learner()["goals"], ["understand attention"])

    def test_loading_nlp_ignores_malformed_cloud_mastery_content(self):
        root = temp_root(self)
        store = LearnerStore(root)
        store.save_mastery("nlp", {"schema_version": 1, "domain": "nlp", "concepts": {}})
        cloud_path = root / "mastery" / "cloud.yaml"
        cloud_path.write_text("not valid JSON", encoding="utf-8")

        nlp = store.load_mastery("nlp")

        self.assertEqual(nlp, {"schema_version": 1, "domain": "nlp", "concepts": {}})
