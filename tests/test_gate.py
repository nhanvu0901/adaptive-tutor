import unittest

from skills.adaptive_tutor.scripts.memory_gate import gate_delta


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


def mastery_state(domain="nlp", concepts=None):
    return {"schema_version": 1, "domain": domain, "concepts": concepts or {}}


def mastery_delta(**overrides):
    entry = {
        "domain": "nlp",
        "concept": "embeddings",
        "to": "can_explain",
        "confidence": 0.8,
        "evidence_type": "explanation",
        "strength": "strong",
        "max_hint_level": 1,
    }
    entry.update(overrides)
    return {"schema_version": 1, "mastery": [entry]}


class GateMasteryTests(unittest.TestCase):
    def test_self_report_cannot_promote_to_can_explain(self):
        result = gate_delta(
            mastery_delta(evidence_type="self_report"), learner_state(), {"nlp": mastery_state()}
        )
        self.assertNotIn("mastery", result)

    def test_explanation_can_promote_to_can_explain(self):
        result = gate_delta(mastery_delta(), learner_state(), {"nlp": mastery_state()})
        self.assertEqual(result["mastery"][0]["to"], "can_explain")

    def test_application_can_promote_to_can_apply(self):
        result = gate_delta(
            mastery_delta(to="can_apply", evidence_type="application", max_hint_level=2),
            learner_state(),
            {"nlp": mastery_state()},
        )
        self.assertEqual(result["mastery"][0]["to"], "can_apply")

    def test_transfer_can_promote_to_can_transfer(self):
        result = gate_delta(
            mastery_delta(to="can_transfer", evidence_type="transfer", max_hint_level=1),
            learner_state(),
            {"nlp": mastery_state()},
        )
        self.assertEqual(result["mastery"][0]["to"], "can_transfer")

    def test_heavy_hint_blocks_can_transfer_promotion(self):
        result = gate_delta(
            mastery_delta(to="can_transfer", evidence_type="transfer", max_hint_level=2),
            learner_state(),
            {"nlp": mastery_state()},
        )
        self.assertNotIn("mastery", result)

    def test_recent_strong_contradiction_can_reduce_confidence(self):
        current = mastery_state(concepts={"embeddings": {"state": "can_apply", "confidence": 0.8}})
        result = gate_delta(
            mastery_delta(
                to="can_apply", confidence=0.45, evidence_type="contradiction", strength="strong"
            ),
            learner_state(),
            {"nlp": current},
        )
        self.assertEqual(result["mastery"][0]["confidence"], 0.45)

    def test_duplicate_mastery_promotions_consolidate_to_strongest_state(self):
        weaker = mastery_delta(
            to="can_explain", confidence=0.78, evidence_type="explanation"
        )["mastery"][0]
        stronger = mastery_delta(
            to="can_apply", confidence=0.86, evidence_type="application"
        )["mastery"][0]

        forward = gate_delta(
            {"schema_version": 1, "mastery": [stronger, weaker]},
            learner_state(),
            {"nlp": mastery_state()},
        )
        reverse = gate_delta(
            {"schema_version": 1, "mastery": [weaker, stronger]},
            learner_state(),
            {"nlp": mastery_state()},
        )

        self.assertEqual(forward, reverse)
        self.assertEqual(len(forward["mastery"]), 1)
        self.assertEqual(forward["mastery"][0]["to"], "can_apply")

    def test_lower_state_requires_verified_strong_contradiction(self):
        current = mastery_state(concepts={
            "embeddings": {"state": "can_apply", "confidence": 0.9}
        })
        unverified = mastery_delta(
            to="exposed", confidence=0.3, evidence_type="contradiction", strength="strong"
        )
        verified = mastery_delta(
            to="exposed", confidence=0.3, evidence_type="contradiction", strength="strong",
            verified_at="2026-08-24",
        )

        self.assertNotIn(
            "mastery", gate_delta(unverified, learner_state(), {"nlp": current})
        )
        self.assertEqual(
            gate_delta(verified, learner_state(), {"nlp": current})["mastery"][0]["to"],
            "exposed",
        )


class GatePreferenceTests(unittest.TestCase):
    def preference_delta(self, **overrides):
        entry = {
            "key": "systems_concepts",
            "value": "visual_first",
            "confidence": 0.65,
            "evidence_type": "recognition",
            "strength": "medium",
        }
        entry.update(overrides)
        return {"schema_version": 1, "preferences": [entry]}

    def test_one_inferred_preference_signal_stays_candidate(self):
        result = gate_delta(self.preference_delta(), learner_state(), {})
        self.assertNotIn("preferences", result)
        self.assertEqual(
            result["candidate_preferences"],
            [{
                "key": "systems_concepts", "strategy": "visual_first",
                "evidence_count": 1, "confidence": 0.65,
            }],
        )

    def test_legacy_candidate_count_cannot_confirm_new_strategy(self):
        learner = learner_state(candidate_preferences={
            "systems_concepts": {"evidence_count": 2, "confidence": 0.65}
        })
        result = gate_delta(self.preference_delta(confidence=0.75), learner, {})

        self.assertNotIn("preferences", result)
        self.assertEqual(
            result["candidate_preferences"],
            [{
                "key": "systems_concepts", "strategy": "visual_first",
                "evidence_count": 1, "confidence": 0.75,
            }],
        )

    def test_distinct_inferred_strategies_do_not_combine_or_depend_on_order(self):
        visual = self.preference_delta(confidence=0.70)["preferences"][0]
        worked = self.preference_delta(
            value="worked_examples", confidence=0.72
        )["preferences"][0]

        forward = gate_delta(
            {"schema_version": 1, "preferences": [visual, visual.copy(), worked]},
            learner_state(),
            {},
        )
        reverse = gate_delta(
            {"schema_version": 1, "preferences": [worked, visual, visual.copy()]},
            learner_state(),
            {},
        )

        self.assertEqual(forward, reverse)
        self.assertNotIn("preferences", forward)
        self.assertEqual(forward["candidate_preferences"], [{
            "key": "systems_concepts", "strategy": "visual_first",
            "evidence_count": 2, "confidence": 0.70,
        }])

    def test_new_strategy_starts_separate_candidate_from_prior_strategy(self):
        learner = learner_state(candidate_preferences={
            "systems_concepts": {
                "strategy": "visual_first", "evidence_count": 2, "confidence": 0.70,
            }
        })

        result = gate_delta(
            self.preference_delta(value="worked_examples", confidence=0.72),
            learner,
            {},
        )

        self.assertNotIn("preferences", result)
        self.assertEqual(result["candidate_preferences"], [{
            "key": "systems_concepts", "strategy": "worked_examples",
            "evidence_count": 1, "confidence": 0.72,
        }])

    def test_three_same_delta_signals_promote_one_preference(self):
        entry = self.preference_delta(confidence=0.70)["preferences"][0]
        result = gate_delta(
            {"schema_version": 1, "preferences": [entry, entry.copy(), entry.copy()]},
            learner_state(),
            {},
        )
        self.assertEqual(
            result["preferences"],
            [{"key": "systems_concepts", "strategy": "visual_first", "confidence": 0.70}],
        )
        self.assertNotIn("candidate_preferences", result)

    def test_explicit_preference_promotes_immediately(self):
        result = gate_delta(
            self.preference_delta(evidence_type="explicit_preference", confidence=0.4), learner_state(), {}
        )
        self.assertEqual(
            result["preferences"],
            [{"key": "systems_concepts", "strategy": "visual_first", "confidence": 0.4}],
        )

    def test_goal_change_requires_explicit_user_evidence(self):
        delta = {"schema_version": 1, "profile": [
            {"field": "goals", "value": "learn NLP", "source": "inferred"}
        ]}
        self.assertNotIn("profile", gate_delta(delta, learner_state(), {}))

    def test_empty_delta_returns_no_changes(self):
        self.assertEqual(gate_delta({"schema_version": 1}, learner_state(), {}), {"schema_version": 1})
