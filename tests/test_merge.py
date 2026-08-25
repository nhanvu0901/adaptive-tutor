import copy
import unittest

from skills.adaptive_tutor.scripts.learner_store import LearnerStore
from skills.adaptive_tutor.scripts.merge_delta import apply_checkpoint, merge_learner, merge_mastery
from tests.helpers import temp_root


def learner_state(**overrides):
    learner = {
        "schema_version": 1,
        "permissions": {},
        "goals": [],
        "interests": [],
        "background": [],
        "preferences": {},
        "candidate_preferences": {},
        "constraints": {},
    }
    learner.update(overrides)
    return learner


class MergeTests(unittest.TestCase):
    def test_mastery_replaces_concept_state_instead_of_appending_history(self):
        current = {"schema_version": 1, "domain": "nlp", "concepts": {}}
        result = merge_mastery(current, [{
            "domain": "nlp", "concept": "embeddings", "to": "can_apply",
            "confidence": 0.82, "evidence_type": "application", "strength": "strong",
            "max_hint_level": 1, "verified_at": "2026-08-24",
        }])

        self.assertEqual(result["concepts"]["embeddings"], {
            "state": "can_apply", "confidence": 0.82, "last_verified": "2026-08-24",
            "evidence": {"strongest_type": "application", "count": 1, "max_hint_level": 1},
        })
        self.assertNotIn("history", result["concepts"]["embeddings"])
        self.assertEqual(current["concepts"], {})

    def test_preference_candidate_count_merges_deterministically(self):
        learner = learner_state(candidate_preferences={
            "systems_concepts": {"evidence_count": 1, "confidence": 0.55}
        })
        result = merge_learner(learner, {"schema_version": 1, "candidate_preferences": [{
            "key": "systems_concepts", "strategy": "visual_first",
            "evidence_count": 2, "confidence": 0.65,
        }]})

        self.assertEqual(result["candidate_preferences"]["systems_concepts"],
                         {"strategy": "visual_first", "evidence_count": 2,
                          "confidence": 0.65})

    def test_confirmed_preference_removes_candidate(self):
        result = merge_learner(learner_state(candidate_preferences={
            "systems_concepts": {"evidence_count": 2, "confidence": 0.65}
        }), {"schema_version": 1, "preferences": [{
            "key": "systems_concepts", "strategy": "visual_first", "confidence": 0.75,
        }]})

        self.assertEqual(result["preferences"]["systems_concepts"],
                         {"strategy": "visual_first", "confidence": 0.75})
        self.assertNotIn("systems_concepts", result["candidate_preferences"])

    def test_same_input_state_and_delta_produce_same_output(self):
        learner = learner_state(goals=["learn NLP"])
        delta = {"schema_version": 1, "profile": [
            {"field": "goals", "value": "understand attention", "source": "explicit_user"}
        ]}

        self.assertEqual(merge_learner(learner, delta), merge_learner(learner, delta))

    def test_noop_delta_does_not_change_state(self):
        learner = learner_state(goals=["learn NLP"])
        original = copy.deepcopy(learner)

        self.assertEqual(merge_learner(learner, {"schema_version": 1}), original)
        self.assertEqual(learner, original)

    def test_persistence_failure_leaves_profile_and_mastery_unchanged(self):
        root = temp_root(self)
        initial_store = LearnerStore(root)
        initial_store.load_learner()
        initial_store.save_mastery("nlp", {
            "schema_version": 1, "domain": "nlp", "concepts": {},
        })
        learner_path = root / "LEARNER.yaml"
        mastery_path = root / "mastery" / "nlp.yaml"
        learner_before = learner_path.read_bytes()
        mastery_before = mastery_path.read_bytes()

        class FailingMasteryStore(LearnerStore):
            def save_mastery(self, domain, data):
                raise OSError("simulated mastery write failure")

        delta = {"schema_version": 1, "profile": [{
            "field": "goals", "value": "learn NLP", "source": "explicit_user",
        }], "mastery": [{
            "domain": "nlp", "concept": "embeddings", "to": "can_explain",
            "confidence": 0.8, "evidence_type": "explanation", "strength": "strong",
            "max_hint_level": 1,
        }]}

        with self.assertRaisesRegex(OSError, "simulated mastery write failure"):
            apply_checkpoint(FailingMasteryStore(root), delta)

        self.assertEqual(learner_path.read_bytes(), learner_before)
        self.assertEqual(mastery_path.read_bytes(), mastery_before)

    def test_checkpoint_duplicate_mastery_entries_cannot_downgrade_by_list_order(self):
        stronger = {
            "domain": "nlp", "concept": "embeddings", "to": "can_apply",
            "confidence": 0.86, "evidence_type": "application", "strength": "strong",
            "max_hint_level": 1,
        }
        weaker = {
            "domain": "nlp", "concept": "embeddings", "to": "can_explain",
            "confidence": 0.78, "evidence_type": "explanation", "strength": "strong",
            "max_hint_level": 1,
        }
        results = []
        for entries in ([stronger, weaker], [weaker, stronger]):
            root = temp_root(self)
            store = LearnerStore(root)
            apply_checkpoint(store, {"schema_version": 1, "mastery": entries})
            results.append(store.load_mastery("nlp")["concepts"]["embeddings"])

        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0]["state"], "can_apply")
