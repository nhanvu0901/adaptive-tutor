import unittest

from skills.adaptive_tutor.scripts.model import (
    EVIDENCE_RANK,
    STATE_RANK,
    clamp_confidence,
)


class ModelTests(unittest.TestCase):
    def test_state_order_is_monotonic(self):
        self.assertLess(STATE_RANK["unknown"], STATE_RANK["exposed"])
        self.assertLess(STATE_RANK["exposed"], STATE_RANK["can_explain"])
        self.assertLess(STATE_RANK["can_explain"], STATE_RANK["can_apply"])
        self.assertLess(STATE_RANK["can_apply"], STATE_RANK["can_transfer"])

    def test_transfer_is_stronger_than_self_report(self):
        self.assertGreater(EVIDENCE_RANK["transfer"], EVIDENCE_RANK["self_report"])

    def test_confidence_is_clamped(self):
        self.assertEqual(clamp_confidence(-0.2), 0.0)
        self.assertEqual(clamp_confidence(1.2), 1.0)
        self.assertEqual(clamp_confidence(0.72), 0.72)
