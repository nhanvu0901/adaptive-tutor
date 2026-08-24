"""Python import alias for the portable ``adaptive-tutor`` skill directory."""

from pathlib import Path


__path__ = [str(Path(__file__).resolve().parent.parent / "adaptive-tutor")]
