import copy
import unittest

from skills.adaptive_tutor.scripts.merge_delta import merge_learner, merge_mastery


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
            "key": "systems_concepts", "evidence_count": 2, "confidence": 0.65,
        }]})

        self.assertEqual(result["candidate_preferences"]["systems_concepts"],
                         {"evidence_count": 2, "confidence": 0.65})

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
