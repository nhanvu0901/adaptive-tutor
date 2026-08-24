STATE_RANK = {
    "unknown": 0,
    "exposed": 1,
    "can_explain": 2,
    "can_apply": 3,
    "can_transfer": 4,
}

EVIDENCE_RANK = {
    "self_report": 0,
    "recognition": 1,
    "recall": 2,
    "explanation": 3,
    "application": 4,
    "transfer": 5,
    "repeated_success": 6,
    "contradiction": 6,
    "explicit_preference": 6,
}

STRENGTH_RANK = {"weak": 1, "medium": 2, "strong": 3}
PERMISSIONS = {"allow_once", "allow_and_remember", "deny"}


def clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
