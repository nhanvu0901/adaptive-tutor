"""Evidence-based filtering for durable learner-memory changes."""

from copy import deepcopy

from .model import EVIDENCE_RANK, STATE_RANK


REQUIRED_EVIDENCE = {
    "unknown": "self_report",
    "exposed": "recognition",
    "can_explain": "explanation",
    "can_apply": "application",
    "can_transfer": "transfer",
}

MAX_HINT_LEVEL = {"can_explain": 3, "can_apply": 2, "can_transfer": 1}
PREFERENCE_EVIDENCE_COUNT = 3
PREFERENCE_CONFIDENCE = 0.70


def required_evidence_rank(target_state):
    """Return the minimum evidence rank required to persist *target_state*."""
    return EVIDENCE_RANK[REQUIRED_EVIDENCE[target_state]]


def _current_concept(mastery_by_domain, domain, concept):
    domain_state = mastery_by_domain.get(domain, {})
    return domain_state.get("concepts", {}).get(concept, {"state": "unknown", "confidence": 0.0})


def _accept_mastery(entry, mastery_by_domain):
    current = _current_concept(mastery_by_domain, entry["domain"], entry["concept"])
    current_rank = STATE_RANK[current["state"]]
    target_rank = STATE_RANK[entry["to"]]
    is_strong_contradiction = (
        entry["evidence_type"] == "contradiction" and entry["strength"] == "strong"
    )

    if is_strong_contradiction:
        if entry["confidence"] >= current["confidence"] or target_rank > current_rank:
            return False
        return target_rank == current_rank or "verified_at" in entry

    if target_rank < current_rank:
        return False
    if entry["confidence"] < current["confidence"]:
        return False
    if EVIDENCE_RANK[entry["evidence_type"]] < required_evidence_rank(entry["to"]):
        return False
    max_hint = MAX_HINT_LEVEL.get(entry["to"])
    return max_hint is None or entry.get("max_hint_level", 0) <= max_hint


def _gate_preferences(entries, learner):
    confirmed, candidates = [], []
    existing = learner.get("candidate_preferences", {})
    for entry in entries:
        if entry["evidence_type"] == "explicit_preference":
            confirmed.append({
                "key": entry["key"], "strategy": entry["value"], "confidence": entry["confidence"],
            })
            continue

        prior = existing.get(entry["key"], {})
        count = prior.get("evidence_count", 0) + 1
        confidence = max(prior.get("confidence", 0.0), entry["confidence"])
        if count >= PREFERENCE_EVIDENCE_COUNT and confidence >= PREFERENCE_CONFIDENCE:
            confirmed.append({"key": entry["key"], "strategy": entry["value"], "confidence": confidence})
        else:
            candidates.append({"key": entry["key"], "evidence_count": count, "confidence": confidence})
    return confirmed, candidates


def gate_delta(delta, learner, mastery_by_domain):
    """Return a copy of the durable changes that pass V1 evidence policy."""
    accepted = {"schema_version": delta["schema_version"]}
    mastery = [
        deepcopy(entry) for entry in delta.get("mastery", [])
        if _accept_mastery(entry, mastery_by_domain)
    ]
    if mastery:
        accepted["mastery"] = mastery

    if delta.get("misconceptions"):
        accepted["misconceptions"] = deepcopy(delta["misconceptions"])

    preferences, candidates = _gate_preferences(delta.get("preferences", []), learner)
    if preferences:
        accepted["preferences"] = preferences
    if candidates:
        accepted["candidate_preferences"] = candidates

    profile = [
        deepcopy(entry) for entry in delta.get("profile", [])
        if entry["source"] == "explicit_user"
    ]
    if profile:
        accepted["profile"] = profile
    return accepted
