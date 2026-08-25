"""Deterministic consolidation of evidence-gated learner-memory deltas."""

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from skills.adaptive_tutor.scripts.learner_store import DEFAULT_LEARNER, LearnerStore
from skills.adaptive_tutor.scripts.memory_gate import gate_delta
from skills.adaptive_tutor.scripts.model import EVIDENCE_RANK
from skills.adaptive_tutor.scripts.validate_state import (
    validate_delta,
    validate_learner,
    validate_mastery,
)


MAX_EVIDENCE_COUNT = 3


def merge_mastery(current, accepted_entries):
    """Return a new mastery document with accepted entries replacing concept state."""
    result = deepcopy(current)
    for entry in accepted_entries:
        concept = entry["concept"]
        previous = result["concepts"].get(concept, {})
        previous_evidence = previous.get("evidence", {})
        previous_type = previous_evidence.get("strongest_type")
        evidence_type = entry["evidence_type"]
        strongest_type = evidence_type
        if previous_type and EVIDENCE_RANK[previous_type] > EVIDENCE_RANK[evidence_type]:
            strongest_type = previous_type
        evidence = {
            "strongest_type": strongest_type,
            "count": min(MAX_EVIDENCE_COUNT, previous_evidence.get("count", 0) + 1),
        }
        hint_levels = [value for value in (
            previous_evidence.get("max_hint_level"), entry.get("max_hint_level")
        ) if value is not None]
        if hint_levels:
            evidence["max_hint_level"] = max(hint_levels)
        record = {"state": entry["to"], "confidence": entry["confidence"], "evidence": evidence}
        if "verified_at" in entry:
            record["last_verified"] = entry["verified_at"]
        elif "last_verified" in previous:
            record["last_verified"] = previous["last_verified"]
        result["concepts"][concept] = record
    return result


def merge_learner(learner, accepted_delta):
    """Return a new learner profile with an already-gated delta applied."""
    result = deepcopy(learner)
    for entry in accepted_delta.get("profile", []):
        field, value = entry["field"], entry["value"]
        if field in ("goals", "interests", "background"):
            if value not in result[field]:
                result[field].append(deepcopy(value))
        elif field == "constraints" and isinstance(value, dict):
            result[field].update(deepcopy(value))

    for entry in accepted_delta.get("candidate_preferences", []):
        result["candidate_preferences"][entry["key"]] = {
            "evidence_count": entry["evidence_count"], "confidence": entry["confidence"],
        }
    for entry in accepted_delta.get("preferences", []):
        key = entry["key"]
        result["preferences"][key] = {
            "strategy": entry["strategy"], "confidence": entry["confidence"],
        }
        result["candidate_preferences"].pop(key, None)

    if accepted_delta.get("misconceptions"):
        misconceptions = result["constraints"].setdefault("misconceptions", {})
        for entry in accepted_delta["misconceptions"]:
            misconceptions[entry["concept"]] = entry["status"]
    return result


def _summary(before_learner, after_learner, mastery_before, mastery_after):
    profile_fields = [field for field in ("goals", "interests", "background", "constraints")
                      if before_learner[field] != after_learner[field]]
    misconceptions_before = before_learner["constraints"].get("misconceptions", {})
    misconceptions_after = after_learner["constraints"].get("misconceptions", {})
    misconceptions = sorted(key for key in set(misconceptions_before) | set(misconceptions_after)
                            if misconceptions_before.get(key) != misconceptions_after.get(key))
    mastery_concepts = {
        domain: sorted(concept for concept in set(mastery_before[domain]["concepts"]) |
                       set(mastery_after[domain]["concepts"])
                       if mastery_before[domain]["concepts"].get(concept) !=
                       mastery_after[domain]["concepts"].get(concept))
        for domain in mastery_after
    }
    mastery_concepts = {domain: concepts for domain, concepts in mastery_concepts.items() if concepts}
    written = bool(profile_fields or mastery_concepts or misconceptions)
    return {"profile_fields": profile_fields, "mastery_concepts": mastery_concepts,
            "misconceptions": misconceptions, "written": written}


def _restore_file(path, contents):
    if contents is None:
        if path.exists():
            path.unlink()
        return
    temporary = path.with_suffix(path.suffix + ".rollback")
    temporary.write_bytes(contents)
    temporary.replace(path)


def _persist_all_or_rollback(store, learner_before, learner_after, mastery_before, mastery_after):
    writes = []
    if learner_before != learner_after:
        writes.append((store.learner_path, lambda: store.save_learner(learner_after)))
    for domain, mastery in mastery_after.items():
        if mastery != mastery_before[domain]:
            writes.append((store._mastery_path(domain),
                           lambda domain=domain, mastery=mastery: store.save_mastery(domain, mastery)))
    snapshots = {path: path.read_bytes() if path.exists() else None for path, _ in writes}
    try:
        for _, write in writes:
            write()
    except Exception:
        for path, contents in snapshots.items():
            _restore_file(path, contents)
        raise


def apply_checkpoint(store, delta, dry_run=False):
    """Validate, gate, merge, validate again, and atomically persist a checkpoint."""
    validate_delta(delta)
    learner = (store.load_learner() if store.learner_path.exists()
               else deepcopy(DEFAULT_LEARNER))
    domains = sorted({entry["domain"] for entry in delta.get("mastery", [])})
    mastery_before = {domain: store.load_mastery(domain) for domain in domains}
    accepted = gate_delta(delta, learner, mastery_before)
    merged_learner = merge_learner(learner, accepted)
    mastery_after = {
        domain: merge_mastery(mastery_before[domain], [entry for entry in accepted.get("mastery", [])
                                                        if entry["domain"] == domain])
        for domain in domains
    }
    validate_learner(merged_learner)
    for mastery in mastery_after.values():
        validate_mastery(mastery)
    summary = _summary(learner, merged_learner, mastery_before, mastery_after)
    if not dry_run and summary["written"]:
        _persist_all_or_rollback(store, learner, merged_learner, mastery_before, mastery_after)
    if dry_run:
        summary["written"] = False
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delta", required=True, type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        delta = json.loads(args.delta.read_text(encoding="utf-8"))
        summary = apply_checkpoint(LearnerStore(args.root), delta, args.dry_run)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(summary, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
