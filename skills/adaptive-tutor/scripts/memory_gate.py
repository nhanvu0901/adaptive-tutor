"""Evidence-based filtering for durable learner-memory changes."""

import json
from copy import deepcopy

if __package__ in (None, ""):
    from model import EVIDENCE_RANK, STATE_RANK, STRENGTH_RANK
else:
    from .model import EVIDENCE_RANK, STATE_RANK, STRENGTH_RANK


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


def _canonical_mastery_key(entry, current_rank):
    target_rank = STATE_RANK[entry["to"]]
    lowers_state = target_rank < current_rank
    canonical_json = json.dumps(entry, sort_keys=True, separators=(",", ":"))
    if lowers_state:
        return (
            1,
            entry["verified_at"],
            -target_rank,
            -entry["confidence"],
            canonical_json,
        )
    return (
        0,
        target_rank,
        entry["confidence"],
        EVIDENCE_RANK[entry["evidence_type"]],
        STRENGTH_RANK[entry["strength"]],
        -entry.get("max_hint_level", 0),
        entry.get("verified_at", ""),
        canonical_json,
    )


def gate_mastery_entries(entries, mastery_by_domain):
    """Return one deterministic, policy-compliant entry per domain/concept."""
    grouped = {}
    for entry in entries:
        grouped.setdefault((entry["domain"], entry["concept"]), []).append(entry)

    accepted = []
    for domain, concept in sorted(grouped):
        current = _current_concept(mastery_by_domain, domain, concept)
        eligible = [
            entry for entry in grouped[(domain, concept)]
            if _accept_mastery(entry, mastery_by_domain)
        ]
        if eligible:
            accepted.append(deepcopy(max(
                eligible,
                key=lambda entry: _canonical_mastery_key(
                    entry, STATE_RANK[current["state"]]
                ),
            )))
    return accepted


def _candidate_rank(candidate):
    return (
        candidate["evidence_count"],
        candidate["confidence"],
        candidate.get("strategy", ""),
    )


def _gate_preferences(entries, learner):
    confirmed = []
    candidates = []
    grouped = {}
    for entry in entries:
        grouped.setdefault(entry["key"], []).append(entry)

    stored_candidates = learner.get("candidate_preferences", {})
    for key in sorted(grouped):
        key_entries = grouped[key]
        explicit = [
            entry for entry in key_entries
            if entry["evidence_type"] == "explicit_preference"
        ]
        if explicit:
            winner = max(
                explicit,
                key=lambda entry: (
                    entry["confidence"], STRENGTH_RANK[entry["strength"]], entry["value"]
                ),
            )
            confirmed.append({
                "key": key, "strategy": winner["value"],
                "confidence": winner["confidence"],
            })
            continue

        by_strategy = {}
        for entry in key_entries:
            by_strategy.setdefault(entry["value"], []).append(entry)

        prior = stored_candidates.get(key)
        identity_candidates = []
        for strategy in sorted(by_strategy):
            supporting = by_strategy[strategy]
            count = len(supporting)
            confidence = max(entry["confidence"] for entry in supporting)
            if prior and (
                prior.get("strategy") == strategy
                or ("strategy" not in prior and len(by_strategy) == 1)
            ):
                count += prior["evidence_count"]
                confidence = max(confidence, prior["confidence"])
            identity_candidates.append({
                "key": key, "strategy": strategy,
                "evidence_count": count, "confidence": confidence,
            })

        promotable = [candidate for candidate in identity_candidates if (
            "strategy" in candidate
            and candidate["evidence_count"] >= PREFERENCE_EVIDENCE_COUNT
            and candidate["confidence"] >= PREFERENCE_CONFIDENCE
        )]
        if promotable:
            winner = max(promotable, key=_candidate_rank)
            confirmed.append({
                "key": key, "strategy": winner["strategy"],
                "confidence": winner["confidence"],
            })
        else:
            candidates.append(max(identity_candidates, key=_candidate_rank))
    return confirmed, candidates


def gate_delta(delta, learner, mastery_by_domain):
    """Return a copy of the durable changes that pass V1 evidence policy."""
    accepted = {"schema_version": delta["schema_version"]}
    mastery = gate_mastery_entries(delta.get("mastery", []), mastery_by_domain)
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
