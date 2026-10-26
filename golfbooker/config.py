from __future__ import annotations

from pathlib import Path

import yaml

from .models import Course

ROOT = Path(__file__).resolve().parent.parent


def load_courses(path: Path = ROOT / "config" / "courses.yaml") -> list[Course]:
    data = yaml.safe_load(path.read_text())
    return [Course.from_dict(c) for c in data["courses"]]


def load_settings(path: Path = ROOT / "config" / "settings.yaml") -> dict:
    return yaml.safe_load(path.read_text())
