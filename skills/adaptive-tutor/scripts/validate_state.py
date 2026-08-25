"""Dependency-free validation for durable learner state and lesson deltas."""

if __package__ in (None, ""):
    from model import EVIDENCE_RANK, PERMISSIONS, STATE_RANK, STRENGTH_RANK
else:
    from .model import EVIDENCE_RANK, PERMISSIONS, STATE_RANK, STRENGTH_RANK


class ValidationError(ValueError):
    pass


def _require_mapping(data, label):
    if not isinstance(data, dict):
        raise ValidationError(f"{label} must be an object")


def _require_keys(data, keys, label):
    missing = [key for key in keys if key not in data]
    if missing:
        raise ValidationError(f"{label} missing keys: {', '.join(missing)}")


def _reject_unknown_keys(data, allowed, label):
    unknown = sorted(set(data) - set(allowed))
    if unknown:
        raise ValidationError(f"{label} has unknown keys: {', '.join(unknown)}")


def _require_string(value, label):
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{label} must be a non-empty string")


def _require_list(value, label):
    if not isinstance(value, list):
        raise ValidationError(f"{label} must be a list")


def _require_confidence(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{label} must be a number")
    if not 0.0 <= float(value) <= 1.0:
        raise ValidationError(f"{label} must be between 0 and 1")


def _require_schema_version(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value != 1:
        raise ValidationError(f"unsupported {label} schema_version")


def _validate_evidence(entry, label):
    _require_keys(entry, ["evidence_type", "strength"], label)
    _require_string(entry["evidence_type"], f"{label} evidence_type")
    _require_string(entry["strength"], f"{label} strength")
    if entry["evidence_type"] not in EVIDENCE_RANK:
        raise ValidationError(f"{label} has invalid evidence_type")
    if entry["strength"] not in STRENGTH_RANK:
        raise ValidationError(f"{label} has invalid strength")


def validate_learner(data):
    _require_mapping(data, "learner")
    required = [
        "schema_version", "permissions", "goals", "interests", "background",
        "preferences", "candidate_preferences", "constraints",
    ]
    _require_keys(data, required, "learner")
    _reject_unknown_keys(data, required, "learner")
    _require_schema_version(data["schema_version"], "learner")
    if not isinstance(data["permissions"], dict):
        raise ValidationError("learner permissions must be an object")
    for host, decision in data["permissions"].items():
        _require_string(host, "permission host")
        _require_string(decision, f"permission for {host}")
        if decision == "allow_once":
            raise ValidationError("allow_once is session-only and cannot be persisted")
        if decision not in PERMISSIONS:
            raise ValidationError(f"invalid permission for {host}")
    for field in ("goals", "interests", "background"):
        _require_list(data[field], f"learner {field}")
    for field in ("preferences", "candidate_preferences", "constraints"):
        if not isinstance(data[field], dict):
            raise ValidationError(f"learner {field} must be an object")
    _validate_preferences(data["preferences"], data["candidate_preferences"])
    return data


def _validate_preferences(preferences, candidates):
    for key, preference in preferences.items():
        _require_string(key, "preference key")
        _require_mapping(preference, f"preference {key}")
        _require_keys(preference, ["strategy", "confidence"], f"preference {key}")
        _reject_unknown_keys(preference, ["strategy", "confidence"], f"preference {key}")
        _require_string(preference["strategy"], f"preference {key} strategy")
        _require_confidence(preference["confidence"], f"preference {key} confidence")
    for key, candidate in candidates.items():
        _require_string(key, "candidate preference key")
        _require_mapping(candidate, f"candidate preference {key}")
        _require_keys(candidate, ["evidence_count", "confidence"], f"candidate preference {key}")
        _reject_unknown_keys(
            candidate, ["strategy", "evidence_count", "confidence"],
            f"candidate preference {key}",
        )
        if "strategy" in candidate:
            _require_string(candidate["strategy"], f"candidate preference {key} strategy")
        count = candidate["evidence_count"]
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValidationError(f"candidate preference {key} evidence_count must be a non-negative integer")
        _require_confidence(candidate["confidence"], f"candidate preference {key} confidence")


def validate_mastery(data):
    _require_mapping(data, "mastery")
    required = ["schema_version", "domain", "concepts"]
    _require_keys(data, required, "mastery")
    _reject_unknown_keys(data, required, "mastery")
    _require_schema_version(data["schema_version"], "mastery")
    _require_string(data["domain"], "mastery domain")
    if not isinstance(data["concepts"], dict):
        raise ValidationError("mastery concepts must be an object")
    for concept, record in data["concepts"].items():
        _require_string(concept, "mastery concept")
        _require_mapping(record, f"mastery concept {concept}")
        _require_keys(record, ["state", "confidence"], f"mastery concept {concept}")
        _reject_unknown_keys(record, ["state", "confidence", "last_verified", "evidence"], f"mastery concept {concept}")
        _require_string(record["state"], f"mastery concept {concept} state")
        if record["state"] not in STATE_RANK:
            raise ValidationError(f"invalid state for {concept}")
        _require_confidence(record["confidence"], f"mastery concept {concept} confidence")
        if "last_verified" in record:
            _require_string(record["last_verified"], f"mastery concept {concept} last_verified")
        if "evidence" in record:
            _validate_mastery_evidence(record["evidence"], concept)
    return data


def _validate_mastery_evidence(evidence, concept):
    _require_mapping(evidence, f"mastery concept {concept} evidence")
    _require_keys(evidence, ["strongest_type", "count"], f"mastery concept {concept} evidence")
    _reject_unknown_keys(evidence, ["strongest_type", "count", "max_hint_level"], f"mastery concept {concept} evidence")
    _require_string(evidence["strongest_type"], f"mastery concept {concept} strongest_type")
    if evidence["strongest_type"] not in EVIDENCE_RANK:
        raise ValidationError(f"invalid evidence type for {concept}")
    count = evidence["count"]
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValidationError(f"mastery concept {concept} evidence count must be a non-negative integer")
    if "max_hint_level" in evidence:
        hint = evidence["max_hint_level"]
        if isinstance(hint, bool) or not isinstance(hint, int) or not 0 <= hint <= 6:
            raise ValidationError(f"mastery concept {concept} max_hint_level must be between 0 and 6")


def validate_delta(data):
    _require_mapping(data, "delta")
    allowed = ["schema_version", "mastery", "misconceptions", "preferences", "profile"]
    _require_keys(data, ["schema_version"], "delta")
    _reject_unknown_keys(data, allowed, "delta")
    _require_schema_version(data["schema_version"], "delta")
    for field in ("mastery", "misconceptions", "preferences", "profile"):
        if field in data:
            _require_list(data[field], f"delta {field}")
    for entry in data.get("mastery", []):
        _validate_mastery_delta(entry)
    for entry in data.get("misconceptions", []):
        _validate_misconception_delta(entry)
    for entry in data.get("preferences", []):
        _validate_preference_delta(entry)
    for entry in data.get("profile", []):
        _validate_profile_delta(entry)
    return data


def _validate_mastery_delta(entry):
    _require_mapping(entry, "mastery delta entry")
    required = ["domain", "concept", "confidence", "evidence_type", "strength"]
    _require_keys(entry, required, "mastery delta entry")
    _reject_unknown_keys(entry, required + ["from", "to", "max_hint_level", "verified_at"], "mastery delta entry")
    _require_string(entry["domain"], "mastery delta domain")
    _require_string(entry["concept"], "mastery delta concept")
    _require_keys(entry, ["to"], "mastery delta entry")
    for field in ("to", "from"):
        if field in entry:
            _require_string(entry[field], f"mastery delta entry {field}")
        if field in entry and entry[field] not in STATE_RANK:
            raise ValidationError(f"mastery delta entry has invalid {field}")
    _require_confidence(entry["confidence"], "mastery delta confidence")
    _validate_evidence(entry, "mastery delta entry")
    if "max_hint_level" in entry:
        hint = entry["max_hint_level"]
        if isinstance(hint, bool) or not isinstance(hint, int) or not 0 <= hint <= 6:
            raise ValidationError("mastery delta max_hint_level must be between 0 and 6")
    if "verified_at" in entry:
        _require_string(entry["verified_at"], "mastery delta verified_at")


def _validate_misconception_delta(entry):
    _require_mapping(entry, "misconception delta entry")
    _require_keys(entry, ["concept", "status"], "misconception delta entry")
    _reject_unknown_keys(entry, ["concept", "status"], "misconception delta entry")
    _require_string(entry["concept"], "misconception delta concept")
    _require_string(entry["status"], "misconception delta status")
    if entry["status"] not in {"discovered", "corrected"}:
        raise ValidationError("misconception delta status must be discovered or corrected")


def _validate_preference_delta(entry):
    _require_mapping(entry, "preference delta entry")
    required = ["key", "value", "confidence", "evidence_type", "strength"]
    _require_keys(entry, required, "preference delta entry")
    _reject_unknown_keys(entry, required + ["source"], "preference delta entry")
    _require_string(entry["key"], "preference delta key")
    _require_string(entry["value"], "preference delta value")
    _require_confidence(entry["confidence"], "preference delta confidence")
    _validate_evidence(entry, "preference delta entry")
    if "source" in entry:
        _require_string(entry["source"], "preference delta source")


def _validate_profile_delta(entry):
    _require_mapping(entry, "profile delta entry")
    _require_keys(entry, ["field", "value", "source"], "profile delta entry")
    _reject_unknown_keys(entry, ["field", "value", "source"], "profile delta entry")
    _require_string(entry["field"], "profile delta field")
    if entry["field"] not in {"goals", "interests", "background", "constraints"}:
        raise ValidationError("profile delta entry has invalid field")
    _require_string(entry["source"], "profile delta source")
    if entry["source"] != "explicit_user":
        raise ValidationError("profile delta source must be explicit_user")
