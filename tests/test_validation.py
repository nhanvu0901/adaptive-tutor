import unittest

from skills.adaptive_tutor.scripts.validate_state import (
    ValidationError,
    validate_delta,
    validate_learner,
    validate_mastery,
)


class ValidationTests(unittest.TestCase):
    def test_valid_learner(self):
        validate_learner({
            "schema_version": 1,
            "permissions": {"claude_global": "deny", "codex_global": "deny"},
            "goals": [],
            "interests": [],
            "background": [],
            "preferences": {},
            "candidate_preferences": {},
            "constraints": {},
        })

    def test_candidate_preference_may_record_strategy_identity(self):
        validate_learner({
            "schema_version": 1,
            "permissions": {},
            "goals": [],
            "interests": [],
            "background": [],
            "preferences": {},
            "candidate_preferences": {
                "systems_concepts": {
                    "strategy": "visual_first", "evidence_count": 2, "confidence": 0.65,
                }
            },
            "constraints": {},
        })

    def test_allow_once_cannot_be_persisted(self):
        with self.assertRaises(ValidationError):
            validate_learner({
                "schema_version": 1,
                "permissions": {"claude_global": "allow_once"},
                "goals": [], "interests": [], "background": [],
                "preferences": {}, "candidate_preferences": {}, "constraints": {},
            })

    def test_mastery_rejects_unknown_state_name(self):
        with self.assertRaises(ValidationError):
            validate_mastery({
                "schema_version": 1,
                "domain": "nlp",
                "concepts": {"attention": {"state": "expert", "confidence": 0.8}},
            })

    def test_delta_requires_schema_version(self):
        with self.assertRaises(ValidationError):
            validate_delta({"mastery": []})

    def test_mastery_rejects_out_of_range_confidence(self):
        with self.assertRaises(ValidationError):
            validate_mastery({
                "schema_version": 1,
                "domain": "nlp",
                "concepts": {
                    "attention": {"state": "can_apply", "confidence": 1.1},
                },
            })

    def test_delta_rejects_unknown_evidence_type(self):
        with self.assertRaises(ValidationError):
            validate_delta({
                "schema_version": 1,
                "mastery": [{
                    "domain": "nlp",
                    "concept": "attention",
                    "to": "can_apply",
                    "confidence": 0.8,
                    "evidence_type": "intuition",
                    "strength": "strong",
                }],
            })

    def test_delta_rejects_malformed_preference_evidence(self):
        with self.assertRaises(ValidationError):
            validate_delta({
                "schema_version": 1,
                "preferences": [{
                    "key": "systems_concepts",
                    "value": "visual_first",
                    "confidence": 0.8,
                    "evidence_type": "explanation",
                }],
            })

    def test_delta_rejects_non_list_mastery_and_misconceptions(self):
        for field in ("mastery", "misconceptions"):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError):
                    validate_delta({"schema_version": 1, field: {}})

    def test_delta_requires_to_as_the_canonical_mastery_target(self):
        with self.assertRaises(ValidationError):
            validate_delta({
                "schema_version": 1,
                "mastery": [{
                    "domain": "nlp",
                    "concept": "attention",
                    "state": "can_apply",
                    "confidence": 0.8,
                    "evidence_type": "application",
                    "strength": "strong",
                }],
            })

    def test_malformed_state_and_evidence_values_raise_validation_error(self):
        with self.assertRaises(ValidationError):
            validate_mastery({
                "schema_version": 1,
                "domain": "nlp",
                "concepts": {"attention": {"state": [], "confidence": 0.8}},
            })
        with self.assertRaises(ValidationError):
            validate_delta({
                "schema_version": 1,
                "mastery": [{
                    "domain": "nlp",
                    "concept": "attention",
                    "to": "can_apply",
                    "confidence": 0.8,
                    "evidence_type": {},
                    "strength": "strong",
                }],
            })

    def test_delta_rejects_boolean_schema_version(self):
        with self.assertRaises(ValidationError):
            validate_delta({"schema_version": True})
