"""Local, durable storage for the shared Adaptive Tutor learner model."""

import json
import re
from copy import deepcopy
from datetime import date as date_type
from pathlib import Path

if __package__ in (None, ""):
    from model import PERMISSIONS
    from validate_state import validate_learner, validate_mastery
else:
    from .model import PERMISSIONS
    from .validate_state import validate_learner, validate_mastery


DEFAULT_LEARNER = {
    "schema_version": 1,
    "permissions": {},
    "goals": [],
    "interests": [],
    "background": [],
    "preferences": {},
    "candidate_preferences": {},
    "constraints": {},
}


class LearnerStore:
    def __init__(self, root=None):
        self.root = Path(root) if root else Path.home() / ".adaptive-tutor"

    @property
    def learner_path(self):
        return self.root / "LEARNER.yaml"

    def _atomic_write_json(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temp.replace(path)

    def _atomic_write_text(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(text, encoding="utf-8")
        temp.replace(path)

    @staticmethod
    def _read_json(path):
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _slug(value):
        if not isinstance(value, str):
            raise ValueError("slug source must be a string")
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        if not slug:
            raise ValueError("slug source must contain letters or numbers")
        return slug

    def _mastery_path(self, domain):
        return self.root / "mastery" / f"{self._slug(domain)}.yaml"

    def load_learner(self):
        if not self.learner_path.exists():
            data = deepcopy(DEFAULT_LEARNER)
            self.save_learner(data)
            return data
        return validate_learner(self._read_json(self.learner_path))

    def save_learner(self, data):
        validate_learner(data)
        if self.learner_path.exists():
            self.load_learner()
        self._atomic_write_json(self.learner_path, data)

    def get_permission(self, host):
        return self.load_learner()["permissions"].get(host)

    def set_permission(self, host, decision):
        if decision not in PERMISSIONS:
            raise ValueError(f"invalid permission: {decision}")
        if decision == "allow_once":
            return
        learner = self.load_learner()
        learner["permissions"][host] = decision
        self.save_learner(learner)

    def load_mastery(self, domain):
        path = self._mastery_path(domain)
        if not path.exists():
            return {"schema_version": 1, "domain": domain, "concepts": {}}
        data = validate_mastery(self._read_json(path))
        if data["domain"] != domain:
            raise ValueError("stored mastery domain does not match the requested domain")
        return data

    def save_mastery(self, domain, data):
        if data.get("domain") != domain:
            raise ValueError("mastery domain must match the requested domain")
        validate_mastery(data)
        path = self._mastery_path(domain)
        if path.exists():
            self.load_mastery(domain)
        self._atomic_write_json(path, data)

    def archive_session(self, topic, markdown, date=None):
        if not isinstance(markdown, str):
            raise ValueError("session archive must be markdown text")
        if date is None:
            archive_date = date_type.today().isoformat()
        elif isinstance(date, date_type):
            archive_date = date.isoformat()
        elif isinstance(date, str):
            try:
                archive_date = date_type.fromisoformat(date).isoformat()
            except ValueError as error:
                raise ValueError("session date must be an ISO calendar date") from error
        else:
            raise ValueError("session date must be a date or ISO date string")
        path = self.root / "sessions" / f"{archive_date}-{self._slug(topic)}.md"
        self._atomic_write_text(path, markdown)
        return path
